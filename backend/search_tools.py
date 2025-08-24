from typing import Dict, Any, Optional, Protocol, List
from abc import ABC, abstractmethod
from vector_store import VectorStore, SearchResults


class Tool(ABC):
    """Abstract base class for all tools"""
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters"""
        pass


class CourseSearchTool(Tool):
    """Tool for searching course content with semantic course name matching"""
    
    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last search
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "search_course_content",
            "description": "Search course materials with smart course name matching and lesson filtering",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "What to search for in the course content"
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"
                    },
                    "lesson_number": {
                        "type": "integer",
                        "description": "Specific lesson number to search within (e.g. 1, 2, 3)"
                    }
                },
                "required": ["query"]
            }
        }
    
    def execute(self, query: str, course_name: Optional[str] = None, lesson_number: Optional[int] = None) -> str:
        """
        Execute the search tool with given parameters.
        
        Args:
            query: What to search for
            course_name: Optional course filter
            lesson_number: Optional lesson filter
            
        Returns:
            Formatted search results or error message
        """
        
        # Use the vector store's unified search interface
        results = self.store.search(
            query=query,
            course_name=course_name,
            lesson_number=lesson_number
        )
        
        # Handle errors
        if results.error:
            return results.error
        
        # Handle empty results
        if results.is_empty():
            filter_info = ""
            if course_name:
                filter_info += f" in course '{course_name}'"
            if lesson_number:
                filter_info += f" in lesson {lesson_number}"
            return f"No relevant content found{filter_info}."
        
        # Format and return results
        return self._format_results(results)
    
    def _format_results(self, results: SearchResults) -> str:
        """Format search results with course and lesson context"""
        formatted = []
        sources = []  # Track sources for the UI with enhanced metadata
        
        # Cache course metadata to avoid repeated lookups
        course_lessons_cache = {}
        
        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get('course_title', 'unknown')
            lesson_num = meta.get('lesson_number')
            
            # Build context header
            header = f"[{course_title}"
            if lesson_num is not None:
                header += f" - Lesson {lesson_num}"
            header += "]"
            
            # Get lesson link if available
            lesson_link = None
            if course_title and course_title != 'unknown' and lesson_num is not None:
                # Fetch course metadata if not cached
                if course_title not in course_lessons_cache:
                    course_metadata = self._get_course_metadata(course_title)
                    course_lessons_cache[course_title] = course_metadata
                
                # Look for lesson link in cached metadata
                if course_lessons_cache[course_title]:
                    lessons = course_lessons_cache[course_title].get('lessons', [])
                    for lesson in lessons:
                        if lesson.get('lesson_number') == lesson_num:
                            lesson_link = lesson.get('lesson_link')
                            break
            
            # Build source object with enhanced metadata
            source_obj = {
                'display_text': course_title if lesson_num is None else f"{course_title} - Lesson {lesson_num}",
                'course_title': course_title,
                'lesson_number': lesson_num,
                'lesson_link': lesson_link
            }
            sources.append(source_obj)
            
            formatted.append(f"{header}\n{doc}")
        
        # Store enhanced sources for retrieval
        self.last_sources = sources
        
        return "\n\n".join(formatted)
    
    def _get_course_metadata(self, course_title: str) -> Dict[str, Any]:
        """Get course metadata including lesson links from vector store"""
        try:
            # Query the course catalog for this specific course
            all_courses = self.store.get_all_courses_metadata()
            for course_meta in all_courses:
                if course_meta.get('title') == course_title:
                    return course_meta
            return {}
        except Exception as e:
            print(f"Error getting course metadata: {e}")
            return {}

class CourseOutlineTool(Tool):
    """Tool for retrieving course outlines and structure information"""
    
    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last operation
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "get_course_outline",
            "description": "Get structured course outline with lessons, instructor, and links",
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_name": {
                        "type": "string",
                        "description": "Course title to get outline for (partial matches work). Leave empty to get all courses."
                    }
                },
                "required": []
            }
        }
    
    def execute(self, course_name: Optional[str] = None) -> str:
        """
        Execute the course outline tool.
        
        Args:
            course_name: Optional course name to filter by
            
        Returns:
            Formatted course outline(s) or error message
        """
        
        # Get all courses metadata
        all_courses = self.store.get_all_courses_metadata()
        
        if not all_courses:
            return "No courses available in the knowledge base."
        
        # If course name provided, filter to specific course
        if course_name:
            # Use semantic search to find best matching course
            resolved_title = self.store._resolve_course_name(course_name)
            if not resolved_title:
                return f"No course found matching '{course_name}'."
            
            # Find the specific course
            for course in all_courses:
                if course.get('title') == resolved_title:
                    return self._format_single_course(course)
            
            return f"Course metadata not found for '{resolved_title}'."
        
        # Return all courses outline
        return self._format_all_courses(all_courses)
    
    def _format_single_course(self, course: Dict[str, Any]) -> str:
        """Format a single course outline"""
        lines = []
        
        # Course header
        title = course.get('title', 'Unknown Course')
        lines.append(f"## {title}")
        
        # Course link
        if course.get('course_link'):
            lines.append(f"**Course Link:** {course['course_link']}")
        
        # Instructor
        if course.get('instructor'):
            lines.append(f"**Instructor:** {course['instructor']}")
        
        # Lessons
        lessons = course.get('lessons', [])
        if lessons:
            lines.append("\n**Lessons:**")
            for lesson in lessons:
                lesson_num = lesson.get('lesson_number', '?')
                lesson_title = lesson.get('lesson_title', 'Untitled')
                lesson_link = lesson.get('lesson_link', '')
                
                if lesson_link:
                    lines.append(f"- Lesson {lesson_num}: [{lesson_title}]({lesson_link})")
                else:
                    lines.append(f"- Lesson {lesson_num}: {lesson_title}")
        else:
            lines.append("\n*No lessons found for this course.*")
        
        # Track this as a source
        self.last_sources = [{
            'display_text': title,
            'course_title': title,
            'lesson_number': None,
            'lesson_link': course.get('course_link')
        }]
        
        return "\n".join(lines)
    
    def _format_all_courses(self, courses: List[Dict[str, Any]]) -> str:
        """Format all courses outline"""
        if not courses:
            return "No courses available."
        
        lines = ["# Available Courses\n"]
        sources = []
        
        for course in courses:
            title = course.get('title', 'Unknown Course')
            instructor = course.get('instructor', 'Unknown')
            lessons = course.get('lessons', [])
            course_link = course.get('course_link')
            
            # Course summary
            lines.append(f"## {title}")
            if course_link:
                lines.append(f"**Link:** {course_link}")
            lines.append(f"**Instructor:** {instructor}")
            lines.append(f"**Total Lessons:** {len(lessons)}")
            
            # Add to sources
            sources.append({
                'display_text': title,
                'course_title': title,
                'lesson_number': None,
                'lesson_link': course_link
            })
            
            # Lesson titles (compact view)
            if lessons:
                lesson_titles = [f"L{l.get('lesson_number', '?')}: {l.get('lesson_title', 'Untitled')}" 
                               for l in lessons[:3]]  # Show first 3 lessons
                lines.append(f"**Topics:** {', '.join(lesson_titles)}")
                if len(lessons) > 3:
                    lines.append(f"*... and {len(lessons) - 3} more lessons*")
            
            lines.append("")  # Empty line between courses
        
        # Track sources
        self.last_sources = sources
        
        return "\n".join(lines)


class ToolManager:
    """Manages available tools for the AI"""
    
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, tool: Tool):
        """Register any tool that implements the Tool interface"""
        tool_def = tool.get_tool_definition()
        tool_name = tool_def.get("name")
        if not tool_name:
            raise ValueError("Tool must have a 'name' in its definition")
        self.tools[tool_name] = tool

    
    def get_tool_definitions(self) -> list:
        """Get all tool definitions for Anthropic tool calling"""
        return [tool.get_tool_definition() for tool in self.tools.values()]
    
    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"
        
        return self.tools[tool_name].execute(**kwargs)
    
    def get_last_sources(self) -> list:
        """Get sources from the last search operation"""
        # Check all tools for last_sources attribute
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources') and tool.last_sources:
                return tool.last_sources
        return []

    def reset_sources(self):
        """Reset sources from all tools that track sources"""
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources'):
                tool.last_sources = []