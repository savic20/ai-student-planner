"""
Reflector Agent
---------------
AI agent that analyzes user feedback and adjusts study plans.

WHAT THIS DOES:
1. Takes user feedback about a week
2. Analyzes completion rates and difficulty
3. Detects patterns (e.g., "Mondays are hard")
4. Suggests specific adjustments
5. Learns user's optimal study patterns

WHY THIS MATTERS:
- Makes plans adaptive, not static
- Learns from user behavior
- Prevents burnout
- Optimizes study efficiency
"""

import json
import logging
from typing import Dict, Any, List, Optional

from app.llm import get_llm_gateway
from app.models.feedback import (
    FeedbackSubmission,
    ReflectionAnalysis,
    ReflectionInsight,
    AdjustmentType,
    DifficultyLevel
)

logger = logging.getLogger(__name__)


class ReflectorAgent:
    """
    Agent that reflects on user feedback and suggests improvements.
    
    USAGE:
    agent = ReflectorAgent()
    analysis = await agent.analyze_feedback(feedback_data, plan_data)
    """
    
    def __init__(self):
        """Initialize reflector agent"""
        self.llm_gateway = get_llm_gateway()
        logger.info("Reflector Agent initialized")
    
    def _build_reflection_prompt(
        self,
        feedback: FeedbackSubmission,
        plan_data: Dict[str, Any],
        previous_feedback: List[FeedbackSubmission] = None
    ) -> str:
        """
        Build the LLM prompt for feedback analysis.
        
        PROMPT COMPONENTS:
        - Current week's feedback
        - Plan structure
        - Historical feedback (if available)
        - Analysis requirements
        """
        # Calculate completion rate
        completion_rate = (feedback.tasks_completed / feedback.tasks_total * 100) if feedback.tasks_total > 0 else 0
        
        # Build prompt
        prompt = f"""Analyze this student's weekly feedback and suggest plan adjustments.

WEEK {feedback.week_number} FEEDBACK:
- Difficulty: {feedback.difficulty.value}
- Tasks Completed: {feedback.tasks_completed}/{feedback.tasks_total} ({completion_rate:.0f}%)
- Challenges: {feedback.challenges or "None mentioned"}
- What Worked: {feedback.what_worked or "None mentioned"}
- Suggested Changes: {feedback.suggested_changes or "None mentioned"}

CURRENT PLAN STRUCTURE:
Total weeks: {len(plan_data.get('weeks', []))}
Study hours per day: {plan_data.get('preferences', {}).get('study_hours_per_day', 'unknown')}
"""

        # Add historical context if available
        if previous_feedback:
            prompt += f"\nHISTORICAL FEEDBACK ({len(previous_feedback)} previous weeks):\n"
            for prev in previous_feedback[-3:]:  # Last 3 weeks
                prev_rate = (prev.tasks_completed / prev.tasks_total * 100) if prev.tasks_total > 0 else 0
                prompt += f"- Week {prev.week_number}: {prev.difficulty.value}, {prev_rate:.0f}% completed\n"
        
        prompt += """
ANALYZE AND PROVIDE:
1. Summary of the issue (1-2 sentences)
2. Specific insights with recommendations
3. Overall adjustment type needed
4. Concrete parameters to change

Return ONLY valid JSON in this format:
{
  "summary": "string",
  "insights": [
    {
      "observation": "string",
      "recommendation": "string", 
      "adjustment_type": "reduce_workload|increase_workload|redistribute_tasks|add_breaks|change_schedule|no_change",
      "confidence": 0.0-1.0
    }
  ],
  "overall_adjustment": "reduce_workload|increase_workload|redistribute_tasks|add_breaks|change_schedule|no_change",
  "adjustments": {
    "reduce_daily_hours": number or null,
    "add_buffer_days": number or null,
    "redistribute_from": "monday|tuesday|etc" or null,
    "redistribute_to": "day" or null
  },
  "patterns": ["string"]
}

ADJUSTMENT GUIDELINES:
- If completion < 60%: reduce_workload (reduce daily hours by 0.5-1)
- If difficulty = hard/very_hard: reduce_workload or redistribute_tasks
- If difficulty = easy/very_easy: can increase_workload
- If completion > 90% and easy: increase_workload
- Look for day-of-week patterns in challenges

Return ONLY the JSON, no other text:"""
        
        return prompt
    
    async def analyze_feedback(
        self,
        feedback: FeedbackSubmission,
        plan_data: Dict[str, Any],
        previous_feedback: List[FeedbackSubmission] = None,
        max_retries: int = 2
    ) -> ReflectionAnalysis:
        """
        Analyze user feedback and generate recommendations.
        
        ARGS:
        - feedback: Current week's feedback
        - plan_data: The study plan structure
        - previous_feedback: Historical feedback for context
        - max_retries: Retry attempts
        
        RETURNS:
        ReflectionAnalysis with insights and adjustments
        
        EXAMPLE:
        agent = ReflectorAgent()
        analysis = await agent.analyze_feedback(
            feedback=user_feedback,
            plan_data=plan.plan_data
        )
        print(analysis.summary)
        """
        logger.info(f"Analyzing feedback for week {feedback.week_number}...")
        
        # Build prompt
        prompt = self._build_reflection_prompt(feedback, plan_data, previous_feedback)
        
        # Try analysis with retries
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Analysis attempt {attempt + 1}/{max_retries + 1}")
                
                # Call LLM
                response = await self.llm_gateway.generate(
                    prompt=prompt,
                    max_tokens=1500,
                    temperature=0.2  # Low temperature for consistent analysis
                )
                
                logger.info(f"LLM response received ({response.usage['total_tokens']} tokens)")
                
                # Extract JSON
                json_data = self._extract_json(response.content)
                
                # Validate and convert to Pydantic model
                analysis = ReflectionAnalysis(**json_data)
                
                logger.info(
                    f"✅ Analysis complete: {analysis.overall_adjustment.value}, "
                    f"{len(analysis.insights)} insights"
                )
                
                return analysis
            
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed on attempt {attempt + 1}: {e}")
                if attempt >= max_retries:
                    # Return a basic analysis if LLM fails
                    return self._create_fallback_analysis(feedback)
            
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt >= max_retries:
                    return self._create_fallback_analysis(feedback)
        
        return self._create_fallback_analysis(feedback)
    
    def _extract_json(self, llm_response: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response.
        
        Same logic as planner agent - handles markdown, etc.
        """
        import re
        
        text = llm_response.strip()
        
        # Remove markdown
        if text.startswith("```"):
            text = text[3:]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        
        if text.endswith("```"):
            text = text[:-3].strip()
        
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
        
        json_text = text[start:end]
        
        # Try to parse
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            # Try fixing common issues
            fixed = re.sub(r',(\s*[}\]])', r'\1', json_text)
            return json.loads(fixed)
    
    def _create_fallback_analysis(self, feedback: FeedbackSubmission) -> ReflectionAnalysis:
        """
        Create a basic analysis if LLM fails.
        
        Uses simple heuristics based on completion rate and difficulty.
        """
        completion_rate = (feedback.tasks_completed / feedback.tasks_total * 100) if feedback.tasks_total > 0 else 0
        
        # Determine adjustment based on completion and difficulty
        if completion_rate < 60 or feedback.difficulty in [DifficultyLevel.HARD, DifficultyLevel.VERY_HARD]:
            adjustment = AdjustmentType.REDUCE_WORKLOAD
            summary = f"Week {feedback.week_number} was challenging with {completion_rate:.0f}% completion. Reducing workload."
            adjustments = {"reduce_daily_hours": 0.5}
        elif completion_rate > 90 and feedback.difficulty in [DifficultyLevel.EASY, DifficultyLevel.VERY_EASY]:
            adjustment = AdjustmentType.INCREASE_WORKLOAD
            summary = f"Week {feedback.week_number} was easy with {completion_rate:.0f}% completion. Can increase challenge."
            adjustments = {"reduce_daily_hours": -0.5}  # Negative = increase
        else:
            adjustment = AdjustmentType.NO_CHANGE
            summary = f"Week {feedback.week_number} went well with {completion_rate:.0f}% completion. Maintaining current pace."
            adjustments = {}
        
        return ReflectionAnalysis(
            summary=summary,
            insights=[
                ReflectionInsight(
                    observation=f"Completion rate: {completion_rate:.0f}%, Difficulty: {feedback.difficulty.value}",
                    recommendation="Adjust workload based on performance",
                    adjustment_type=adjustment,
                    confidence=0.7
                )
            ],
            overall_adjustment=adjustment,
            adjustments=adjustments,
            patterns=[]
        )
    
    def detect_patterns(
        self,
        all_feedback: List[FeedbackSubmission]
    ) -> List[str]:
        """
        Detect recurring patterns across multiple weeks.
        
        PATTERNS TO DETECT:
        - Consistent day-of-week struggles
        - Workload trends
        - Time estimation accuracy
        
        EXAMPLE:
        patterns = agent.detect_patterns(feedback_history)
        # Returns: ["Struggles on Mondays", "Underestimates time needed"]
        """
        if not all_feedback:
            return []
        
        patterns = []
        
        # Check if consistently struggling
        hard_weeks = sum(1 for f in all_feedback if f.difficulty in [DifficultyLevel.HARD, DifficultyLevel.VERY_HARD])
        if hard_weeks >= len(all_feedback) * 0.6:
            patterns.append("Consistently finding workload challenging")
        
        # Check completion trend
        avg_completion = sum(f.tasks_completed / f.tasks_total for f in all_feedback if f.tasks_total > 0) / len(all_feedback)
        if avg_completion < 0.7:
            patterns.append("Low task completion rate overall")
        
        # Check for improvement
        if len(all_feedback) >= 3:
            recent_avg = sum(f.tasks_completed / f.tasks_total for f in all_feedback[-3:] if f.tasks_total > 0) / 3
            if recent_avg > avg_completion + 0.15:
                patterns.append("Improving over time")
        
        return patterns


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
async def example_usage():
    """Example of using the Reflector Agent"""
    
    # Sample feedback
    feedback = FeedbackSubmission(
        plan_id=1,
        week_number=1,
        difficulty=DifficultyLevel.HARD,
        tasks_completed=3,
        tasks_total=5,
        challenges="Too much work on Monday, couldn't finish everything",
        what_worked="Evening study sessions were productive",
        suggested_changes="Spread the work more evenly"
    )
    
    # Sample plan data
    plan_data = {
        "weeks": [{"week_number": 1, "tasks": []}],
        "preferences": {"study_hours_per_day": 3}
    }
    
    # Create agent
    agent = ReflectorAgent()
    
    # Analyze
    print("Analyzing feedback...")
    analysis = await agent.analyze_feedback(feedback, plan_data)
    
    # Display results
    print(f"\n✅ Analysis complete!")
    print(f"\nSummary: {analysis.summary}")
    print(f"Overall adjustment: {analysis.overall_adjustment.value}")
    
    print(f"\nInsights ({len(analysis.insights)}):")
    for insight in analysis.insights:
        print(f"  - {insight.observation}")
        print(f"    → {insight.recommendation}")
        print(f"    Confidence: {insight.confidence:.0%}")
    
    print(f"\nAdjustments: {analysis.adjustments}")
    
    if analysis.patterns:
        print(f"\nPatterns detected: {', '.join(analysis.patterns)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())