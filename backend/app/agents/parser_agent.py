"""
Parser Agent
------------
LangGraph agent that extracts structured data from syllabus text.

WHAT THIS DOES:
1. Takes raw syllabus text
2. Uses LLM to extract:
   - Course info (name, code, instructor)
   - Assignments (name, due date, weight)
   - Exams (date, weight, topics)
   - Important dates
3. Returns structured JSON

WHY LANGGRAPH?
- State management (track parsing progress)
- Error handling (retry failed extractions)
- Extensible (can add more extraction steps)
- Observable (see what the agent is doing)
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.llm import get_llm_gateway, LLMMessage, MessageRole
from app.models.syllabus import ParsedSyllabusData, validate_parsed_data

logger = logging.getLogger(__name__)


class ParserAgent:
    """
    Agent that parses syllabus text into structured data.
    
    USAGE:
    agent = ParserAgent()
    parsed_data = await agent.parse_syllabus(raw_text)
    print(parsed_data.course_name)
    """
    
    def __init__(self):
        """Initialize parser agent"""
        self.llm_gateway = get_llm_gateway()
        logger.info("Parser Agent initialized")
    
    def _build_parsing_prompt(self, syllabus_text: str) -> str:
        """
        Build the LLM prompt for parsing.
        
        PROMPT ENGINEERING:
        - Clear instructions
        - JSON schema definition
        - Examples of expected output
        - Explicit format requirements
        """
        prompt = f"""You are a syllabus parsing assistant. Extract structured information from the syllabus text below.

CRITICAL INSTRUCTIONS:
1. Return ONLY valid JSON - no markdown, no code blocks, no extra text
2. Ensure all brackets and braces are properly closed
3. Use double quotes for strings, not single quotes
4. Do not add trailing commas after the last item in arrays or objects
5. For dates, use YYYY-MM-DD format (e.g., 2024-10-15)
6. For weights/percentages, use numbers only (e.g., 20 for 20%)
7. If information is not found, use null

REQUIRED JSON STRUCTURE:
{{
  "course_name": "string or null",
  "course_code": "string or null",
  "instructor": "string or null",
  "semester": "string or null",
  "assignments": [
    {{
      "name": "string",
      "due_date": "YYYY-MM-DD or null",
      "weight": number or null,
      "type": "homework/essay/project/etc or null",
      "description": "string or null"
    }}
  ],
  "exams": [
    {{
      "name": "string",
      "date": "YYYY-MM-DD or null",
      "weight": number or null,
      "type": "midterm/final/quiz/etc or null",
      "topics": []
    }}
  ],
  "important_dates": [
    {{
      "date": "YYYY-MM-DD",
      "event": "string",
      "type": "holiday/deadline/etc or null"
    }}
  ],
  "office_hours": "string or null",
  "textbook": "string or null",
  "grading_policy": "string or null"
}}

SYLLABUS TEXT:
{syllabus_text}

RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT:"""
        
        return prompt
    
    async def parse_syllabus(
        self,
        syllabus_text: str,
        max_retries: int = 2
    ) -> ParsedSyllabusData:
        """
        Parse syllabus text into structured data.
        
        ARGS:
        - syllabus_text: Raw text extracted from PDF/DOCX
        - max_retries: Number of retry attempts if parsing fails
        
        RETURNS:
        ParsedSyllabusData object
        
        RAISES:
        Exception if parsing fails after all retries
        
        EXAMPLE:
        agent = ParserAgent()
        parsed = await agent.parse_syllabus(syllabus_text)
        print(f"Found {len(parsed.assignments)} assignments")
        """
        logger.info("Starting syllabus parsing...")
        
        # Build prompt
        prompt = self._build_parsing_prompt(syllabus_text)
        
        # Try parsing with retries
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Parse attempt {attempt + 1}/{max_retries + 1}")
                
                # Call LLM
                response = await self.llm_gateway.generate(
                    prompt=prompt,
                    max_tokens=3000,  # Increased to prevent truncation
                    temperature=0.1  # Low temperature for consistent extraction
                )
                
                logger.info(f"LLM response received ({response.usage['total_tokens']} tokens)")
                
                # Extract JSON from response
                json_data = self._extract_json(response.content)
                
                # Validate and convert to Pydantic model
                parsed_data = validate_parsed_data(json_data)
                
                logger.info(
                    f"✅ Parsing successful: "
                    f"{len(parsed_data.assignments)} assignments, "
                    f"{len(parsed_data.exams)} exams"
                )
                
                return parsed_data
            
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries:
                    # Retry with more explicit instructions
                    prompt += "\n\nPLEASE ENSURE YOUR RESPONSE IS VALID JSON WITH NO MARKDOWN FORMATTING."
                else:
                    raise Exception(f"Failed to parse JSON from LLM response: {e}")
            
            except ValueError as e:
                logger.warning(f"Data validation failed on attempt {attempt + 1}: {e}")
                if attempt >= max_retries:
                    raise Exception(f"Failed to validate parsed data: {e}")
            
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt >= max_retries:
                    raise
        
        raise Exception("Parsing failed after all retries")
    
    def _extract_json(self, llm_response: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response.
        
        LLMs sometimes wrap JSON in markdown or add commentary.
        This function tries to extract pure JSON.
        
        HANDLES:
        - Markdown code blocks: ```json ... ```
        - Extra text before/after JSON
        - Whitespace
        - Truncated responses
        """
        text = llm_response.strip()
        
        # Remove markdown code blocks
        if "```" in text:
            # Extract content between ``` markers
            import re
            # Pattern to match ```json ... ``` or ``` ... ```
            pattern = r'```(?:json)?\s*(.*?)\s*```'
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                text = matches[0].strip()
        
        # Find JSON object boundaries
        start = text.find("{")
        if start == -1:
            raise json.JSONDecodeError("No JSON object found", text, 0)
        
        # Find the matching closing brace
        brace_count = 0
        end = start
        in_string = False
        escape_next = False
        
        for i in range(start, len(text)):
            char = text[i]
            
            # Handle string escaping
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            # Track if we're inside a string
            if char == '"':
                in_string = not in_string
                continue
            
            # Only count braces outside of strings
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
        
        if brace_count != 0:
            # JSON is incomplete, try to extract what we have
            logger.warning(f"JSON appears incomplete (unmatched braces)")
            # Take everything from start to end of text
            end = len(text)
        
        json_text = text[start:end]
        
        # Log the JSON we're trying to parse (for debugging)
        logger.debug(f"Attempting to parse JSON ({len(json_text)} chars)")
        
        # Parse JSON
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            # Log the problematic JSON section
            error_pos = e.pos
            context_start = max(0, error_pos - 100)
            context_end = min(len(json_text), error_pos + 100)
            context = json_text[context_start:context_end]
            
            logger.error(
                f"JSON parsing failed at position {error_pos}:\n"
                f"Context: ...{context}...\n"
                f"Error: {e.msg}"
            )
            
            # Try one more thing: fix common issues
            try:
                # Remove trailing commas (common LLM mistake)
                import re
                fixed_json = re.sub(r',(\s*[}\]])', r'\1', json_text)
                return json.loads(fixed_json)
            except:
                # Give up, re-raise original error
                raise e
    
    async def extract_summary(self, syllabus_text: str) -> str:
        """
        Generate a brief summary of the syllabus.
        
        USAGE:
        summary = await agent.extract_summary(syllabus_text)
        print(summary)  # "CS 101 with Dr. Smith, 3 exams, 5 homework assignments"
        """
        prompt = f"""Summarize this syllabus in 1-2 sentences. Include:
- Course name and instructor
- Number of major assessments (exams, projects)

Syllabus:
{syllabus_text[:1000]}

Summary:"""
        
        response = await self.llm_gateway.generate(
            prompt=prompt,
            max_tokens=100,
            temperature=0.3
        )
        
        return response.content.strip()


# =============================================================================
# USAGE EXAMPLES
# =============================================================================
async def example_usage():
    """Example of using the Parser Agent"""
    
    # Sample syllabus text
    sample_syllabus = """
    COMPUTER SCIENCE 101 - INTRODUCTION TO PROGRAMMING
    Fall 2024
    
    Instructor: Dr. Jane Smith
    Email: jsmith@university.edu
    Office Hours: Tuesdays 2-4 PM
    
    COURSE DESCRIPTION:
    Introduction to programming using Python.
    
    GRADING:
    - Homework (5 assignments): 30%
    - Midterm Exam: 30%
    - Final Project: 40%
    
    SCHEDULE:
    - Homework 1: Due September 15, 2024
    - Homework 2: Due September 29, 2024
    - Homework 3: Due October 13, 2024
    - Midterm Exam: October 20, 2024
    - Homework 4: Due November 3, 2024
    - Homework 5: Due November 17, 2024
    - Final Project: Due December 10, 2024
    
    IMPORTANT DATES:
    - Thanksgiving Break: November 25-29, 2024
    - Last day of classes: December 6, 2024
    
    TEXTBOOK:
    "Python Programming for Beginners" by John Doe
    """
    
    # Create agent
    agent = ParserAgent()
    
    # Parse syllabus
    print("Parsing syllabus...")
    parsed = await agent.parse_syllabus(sample_syllabus)
    
    # Display results
    print(f"\n✅ Parsing complete!")
    print(f"\nCourse: {parsed.course_name} ({parsed.course_code})")
    print(f"Instructor: {parsed.instructor}")
    print(f"Semester: {parsed.semester}")
    
    print(f"\nAssignments ({len(parsed.assignments)}):")
    for assignment in parsed.assignments:
        print(f"  - {assignment.name} (Due: {assignment.due_date}, Weight: {assignment.weight}%)")
    
    print(f"\nExams ({len(parsed.exams)}):")
    for exam in parsed.exams:
        print(f"  - {exam.name} (Date: {exam.date}, Weight: {exam.weight}%)")
    
    print(f"\nImportant Dates ({len(parsed.important_dates)}):")
    for date in parsed.important_dates:
        print(f"  - {date.date}: {date.event}")
    
    # Generate summary
    print("\nGenerating summary...")
    summary = await agent.extract_summary(sample_syllabus)
    print(f"Summary: {summary}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())