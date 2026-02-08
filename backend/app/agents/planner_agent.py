"""
Planner Agent
-------------
LangGraph agent that creates personalized study schedules.

WHAT THIS DOES:
1. Takes parsed syllabus data
2. Considers user preferences (study hours, breaks, etc.)
3. Generates a week-by-week study plan
4. Distributes work evenly to avoid cramming
5. Accounts for exam prep and project deadlines

PLANNING STRATEGY:
- Work backwards from deadlines
- Allocate more time for harder assignments
- Leave buffer time before exams
- Respect user's study hour limits
- Avoid scheduling on break days
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.llm import get_llm_gateway, LLMMessage, MessageRole
from app.models.syllabus import ParsedSyllabusData
from app.models.plan import StudyPlan, WeekPlan, Task, TaskType

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    Agent that generates study plans.
    
    USAGE:
    agent = PlannerAgent()
    plan = await agent.generate_plan(parsed_syllabus, preferences)
    """
    
    def __init__(self):
        """Initialize planner agent"""
        self.llm_gateway = get_llm_gateway()
        logger.info("Planner Agent initialized")
    
    def _build_planning_prompt(
        self,
        syllabus_data: ParsedSyllabusData,
        preferences: Dict[str, Any]
    ) -> str:
        """
        Build the LLM prompt for plan generation.
        
        PROMPT COMPONENTS:
        - Syllabus data (assignments, exams, dates)
        - User preferences (study hours, available days)
        - Instructions for plan structure
        - JSON schema for response
        """
        # Extract preference values with defaults
        study_hours_per_day = preferences.get("study_hours_per_day", 3)
        study_days = preferences.get("study_days", ["monday", "tuesday", "wednesday", "thursday", "friday"])
        break_days = preferences.get("break_days", [])
        
        # Format syllabus data for prompt
        assignments_text = "\n".join([
            f"  - {a.name}: Due {a.due_date}, Weight: {a.weight}%"
            for a in syllabus_data.assignments
        ])
        
        exams_text = "\n".join([
            f"  - {e.name}: Date {e.date}, Weight: {e.weight}%"
            for e in syllabus_data.exams
        ])
        
        prompt = f"""Create a 4-week study plan for this course.

COURSE: {syllabus_data.course_name}

ASSIGNMENTS (next 4 weeks):
{assignments_text or "None"}

EXAMS (next 4 weeks):
{exams_text or "None"}

Create ONLY 4 weeks of tasks. Each week should have 3-5 tasks maximum.
Study {study_hours_per_day} hours per day on: {', '.join(study_days)}

Return ONLY valid JSON (no markdown):

{{
  "title": "{syllabus_data.course_name} - 4 Week Plan",
  "description": "Study schedule for next 4 weeks",
  "weeks": [
    {{
      "week_number": 1,
      "start_date": "2024-09-01",
      "end_date": "2024-09-07",
      "tasks": [
        {{
          "id": "task_1",
          "title": "Review syllabus",
          "description": null,
          "date": "2024-09-02",
          "duration_minutes": 60,
          "type": "study",
          "status": "pending",
          "priority": 3,
          "related_assignment_id": null
        }}
      ],
      "notes": null
    }}
  ],
  "total_study_hours": 48,
  "preferences": {{}},
  "metadata": {{}}
}}

CRITICAL: 
- Return ONLY 4 weeks
- Maximum 5 tasks per week
- No markdown formatting
- Valid JSON only"""
        
        return prompt
    
    async def generate_plan(
        self,
        syllabus_data: ParsedSyllabusData,
        preferences: Dict[str, Any],
        max_retries: int = 2
    ) -> StudyPlan:
        """
        Generate a study plan.
        
        ARGS:
        - syllabus_data: Parsed syllabus information
        - preferences: User study preferences
        - max_retries: Number of retry attempts
        
        RETURNS:
        StudyPlan object with week-by-week schedule
        
        EXAMPLE:
        agent = PlannerAgent()
        plan = await agent.generate_plan(syllabus_data, {
            "study_hours_per_day": 3,
            "study_days": ["monday", "wednesday", "friday"]
        })
        """
        logger.info("Starting plan generation...")
        
        # Build prompt
        prompt = self._build_planning_prompt(syllabus_data, preferences)
        
        # Try generation with retries
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Plan generation attempt {attempt + 1}/{max_retries + 1}")
                
                # Call LLM
                response = await self.llm_gateway.generate(
                    prompt=prompt,
                    max_tokens=2000,  # Smaller for 4-week plans
                    temperature=0.3  # Moderately creative
                )
                
                logger.info(f"LLM response received ({response.usage['total_tokens']} tokens)")
                logger.debug(f"LLM response content: {response.content[:500]}...")  # Log first 500 chars
                
                # Check if response is empty
                if not response.content or not response.content.strip():
                    logger.error("LLM returned empty response")
                    if attempt >= max_retries:
                        raise Exception("LLM returned empty response after all retries")
                    continue
                
                # Extract JSON
                json_data = self._extract_json(response.content)
                
                # Clean/fix the data before validation
                json_data = self._clean_plan_data(json_data)
                
                # Validate and convert to Pydantic model
                plan = StudyPlan(**json_data)
                
                logger.info(
                    f"✅ Plan generated: "
                    f"{len(plan.weeks)} weeks, "
                    f"{sum(len(w.tasks) for w in plan.weeks)} tasks"
                )
                
                return plan
            
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed on attempt {attempt + 1}: {e}")
                logger.warning(f"LLM response was: {response.content[:1000]}")  # Show first 1000 chars
                if attempt >= max_retries:
                    raise Exception(
                        f"Failed to parse JSON from LLM response: {e}\n"
                        f"Response: {response.content[:500]}"
                    )
            
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt >= max_retries:
                    raise
        
        raise Exception("Plan generation failed after all retries")
    
    def _clean_plan_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean/fix LLM output to match Pydantic schema.
        
        FIXES:
        - Invalid task types → map to valid types
        - String related_assignment_id → null
        - Missing fields → add defaults
        """
        # Map invalid task types to valid ones
        type_mapping = {
            "practice": "study",
            "submission": "homework",
            "exam": "exam_prep",
            "test": "exam_prep",
            "quiz": "exam_prep"
        }
        
        # Clean each week
        if "weeks" in data:
            for week in data["weeks"]:
                if "tasks" in week:
                    for task in week["tasks"]:
                        # Fix task type
                        if "type" in task and task["type"] not in ["reading", "homework", "study", "exam_prep", "project", "review", "break"]:
                            task["type"] = type_mapping.get(task["type"], "study")
                        
                        # Fix related_assignment_id (should be int or null, not string)
                        if "related_assignment_id" in task:
                            if isinstance(task["related_assignment_id"], str):
                                task["related_assignment_id"] = None
        
        return data
    
    def _extract_json(self, llm_response: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response.
        
        HANDLES:
        - Markdown code blocks
        - Extra text
        - Trailing commas
        - Incomplete JSON
        """
        import re
        
        text = llm_response.strip()
        
        # Remove leading markdown backticks (```json or just ```)
        if text.startswith("```"):
            text = text[3:]  # Remove ```
            # Remove language identifier if present (json, JSON, etc.)
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        
        # Remove trailing markdown backticks
        if text.endswith("```"):
            text = text[:-3].strip()
        
        # Also try regex pattern for markdown blocks
        if "```" in text:
            pattern = r'```(?:json)?\s*(.*?)\s*```'
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                text = matches[0].strip()
        
        # Find JSON boundaries
        start = text.find("{")
        if start == -1:
            raise json.JSONDecodeError("No JSON object found", text, 0)
        
        # Find matching closing brace
        brace_count = 0
        end = start
        in_string = False
        escape_next = False
        
        for i in range(start, len(text)):
            char = text[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"':
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
        
        if brace_count != 0:
            logger.warning(f"JSON appears incomplete (unmatched braces: {brace_count})")
            # JSON is truncated, but try to parse what we have anyway
            end = len(text)
        
        json_text = text[start:end]
        
        # Try to parse
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            # Try fixing common issues
            fixed = re.sub(r',(\s*[}\]])', r'\1', json_text)
            try:
                return json.loads(fixed)
            except:
                # Last resort: try to fix incomplete JSON by closing it
                if brace_count > 0:
                    # Add missing closing braces
                    fixed_with_braces = json_text + ('}' * brace_count)
                    try:
                        return json.loads(fixed_with_braces)
                    except:
                        pass
                raise
    
    async def adjust_plan(
        self,
        current_plan: StudyPlan,
        feedback: Dict[str, Any]
    ) -> StudyPlan:
        """
        Adjust an existing plan based on feedback.
        
        USE CASES:
        - User fell behind schedule
        - Assignment took longer than expected
        - Need to redistribute workload
        
        ARGS:
        - current_plan: Existing plan
        - feedback: User feedback about difficulties
        
        RETURNS:
        Adjusted StudyPlan
        """
        # This will be implemented by the Reflector Agent later
        # For now, just return the current plan
        logger.info("Plan adjustment requested (not yet implemented)")
        return current_plan


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
async def example_usage():
    """Example of using the Planner Agent"""
    from app.models.syllabus import Assignment, Exam
    
    # Create sample syllabus data
    syllabus_data = ParsedSyllabusData(
        course_name="Introduction to Computer Science",
        course_code="CS 101",
        instructor="Dr. Smith",
        semester="Fall 2024",
        assignments=[
            Assignment(
                name="Homework 1",
                due_date="2024-09-15",
                weight=10,
                type="homework"
            ),
            Assignment(
                name="Homework 2",
                due_date="2024-10-01",
                weight=10,
                type="homework"
            ),
            Assignment(
                name="Final Project",
                due_date="2024-12-10",
                weight=40,
                type="project"
            )
        ],
        exams=[
            Exam(
                name="Midterm",
                date="2024-10-20",
                weight=20,
                type="midterm"
            ),
            Exam(
                name="Final Exam",
                date="2024-12-15",
                weight=20,
                type="final"
            )
        ]
    )
    
    # User preferences
    preferences = {
        "study_hours_per_day": 3,
        "study_days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
    }
    
    # Create agent
    agent = PlannerAgent()
    
    # Generate plan
    print("Generating study plan...")
    plan = await agent.generate_plan(syllabus_data, preferences)
    
    # Display results
    print(f"\n✅ Plan generated: {plan.title}")
    print(f"Description: {plan.description}")
    print(f"Total weeks: {len(plan.weeks)}")
    print(f"Total tasks: {sum(len(w.tasks) for w in plan.weeks)}")
    print(f"Total study hours: {plan.total_study_hours}")
    
    # Show first week
    if plan.weeks:
        week = plan.weeks[0]
        print(f"\nWeek {week.week_number} ({week.start_date} to {week.end_date}):")
        for task in week.tasks[:5]:  # Show first 5 tasks
            print(f"  - {task.date}: {task.title} ({task.duration_minutes} min)")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())