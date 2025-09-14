import google.generativeai as genai
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Google's Gemini API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **One search per query maximum**
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model, system_instruction=self.SYSTEM_PROMPT)
        
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Prepare API call parameters efficiently
        contents = []
        if conversation_history:
            contents.append({"role": "model", "parts": [conversation_history]})
        contents.append({"role": "user", "parts": [query]})

        # Get response from Gemini
        response = self.model.generate_content(
            contents,
            generation_config={"temperature": 0},
            tools=tools
        )
        
        # Handle tool execution if needed
        if response.candidates[0].finish_reason == "TOOL_CODE":
            return self._handle_tool_execution(response, contents, tool_manager)
        
        # Return direct response
        return response.candidates[0].content.parts[0].text
    
    def _handle_tool_execution(self, initial_response, contents: List, tool_manager):
        """
        Handle execution of tool calls and get follow-up response.
        
        Args:
            initial_response: The response containing tool use requests
            contents: The conversation history
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        # Execute all tool calls and collect results
        tool_results = []
        for tool_call in initial_response.candidates[0].content.parts:
            if tool_call.function_call:
                tool_result = tool_manager.execute_tool(
                    tool_call.function_call.name,
                    **tool_call.function_call.args
                )
                
                tool_results.append({
                    "tool_code": tool_call.function_call.name,
                    "tool_response": {"output": tool_result}
                })
        
        # Add tool results as single message
        if tool_results:
            contents.append({"role": "user", "parts": tool_results})
        
        # Get final response
        final_response = self.model.generate_content(
            contents,
            generation_config={"temperature": 0}
        )
        return final_response.candidates[0].content.parts[0].text