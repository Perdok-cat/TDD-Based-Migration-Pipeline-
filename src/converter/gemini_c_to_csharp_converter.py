"""
Gemini-powered C to C# Converter - High-performance conversion using Google Gemini API
"""
import os
import json
import time
import hashlib
import logging
import requests
import random
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import concurrent.futures
from functools import lru_cache

from ..core.models.c_program import CProgram, CFunction, CVariable, CStruct, CEnum, CDefine


class RateLimiter:
    """Rate limiter for API calls with exponential backoff"""
    
    def __init__(self, max_requests_per_minute: int = 1, max_retries: int = 3):
        self.max_requests_per_minute = max_requests_per_minute
        self.max_retries = max_retries
        self.requests_timestamps = []
        self.logger = logging.getLogger(__name__)
    
    def wait_if_needed(self):
        """Wait if we've exceeded rate limit"""
        current_time = time.time()
        
        # Remove timestamps older than 1 minute
        self.requests_timestamps = [
            ts for ts in self.requests_timestamps 
            if current_time - ts < 60
        ]
        
        # If we're at the limit, wait
        if len(self.requests_timestamps) >= self.max_requests_per_minute:
            oldest_request = min(self.requests_timestamps)
            wait_time = 60 - (current_time - oldest_request) + 1  # +1 second buffer
            self.logger.info(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        
        # Record this request
        self.requests_timestamps.append(current_time)
    
    def handle_quota_error(self, error_response: str, attempt: int) -> bool:
        """Handle quota exceeded error with exponential backoff"""
        if "429" in error_response and "quota" in error_response.lower():
            if attempt < self.max_retries:
                # Extract retry delay from error response
                retry_delay = self._extract_retry_delay(error_response)
                if retry_delay is None:
                    retry_delay = min(60 * (2 ** attempt), 300)  # Max 5 minutes
                
                self.logger.warning(f"Quota exceeded. Retrying in {retry_delay} seconds (attempt {attempt + 1}/{self.max_retries})")
                time.sleep(retry_delay)
                return True
            else:
                self.logger.error(f"Max retries ({self.max_retries}) exceeded for quota error")
                return False
        return False
    
    def _extract_retry_delay(self, error_response: str) -> Optional[int]:
        """Extract retry delay from error response"""
        try:
            # Try to parse JSON response
            if error_response.startswith('{'):
                error_data = json.loads(error_response)
                if 'error' in error_data and 'details' in error_data['error']:
                    for detail in error_data['error']['details']:
                        if detail.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo':
                            retry_info = detail.get('retryDelay', '')
                            if retry_info.endswith('s'):
                                return int(retry_info[:-1])
        except:
            pass
        
        # Fallback: look for "retry in Xs" pattern
        import re
        match = re.search(r'retry in (\d+(?:\.\d+)?)s', error_response, re.IGNORECASE)
        if match:
            return int(float(match.group(1)))
        
        return None


@dataclass
class ConversionChunk:
    """A chunk of code to be converted"""
    chunk_id: str
    content: str
    chunk_type: str  # 'function', 'struct', 'enum', 'global', 'define'
    dependencies: List[str]  # Other chunks this depends on
    priority: int  # Higher = more important


@dataclass
class GeminiResponse:
    """Response from Gemini API"""
    success: bool
    converted_code: str
    explanation: str
    warnings: List[str]
    tokens_used: int
    processing_time: float


class GeminiCToCSharpConverter:
    """
    High-performance C to C# converter using Google Gemini API
    
    Efficiency strategies:
    1. Smart chunking - Break large files into optimal chunks
    2. Dependency-aware processing - Process chunks in correct order
    3. Caching - Cache conversions to avoid re-processing
    4. Parallel processing - Convert multiple chunks simultaneously
    5. Context-aware prompts - Provide rich context for better results
    6. Incremental conversion - Build up converted code progressively
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-pro",
        max_tokens: int = 8192,
        cache_dir: str = ".conversion_cache",
        max_parallel: int = 5,
        chunk_size: int = 2000,
        max_requests_per_minute: int = 1  # Conservative for free tier
    ):
        """
        Initialize Gemini converter
        
        Args:
            api_key: Gemini API key (or set GEMINI_API_KEY env var)
            model: Gemini model to use
            max_tokens: Max tokens per request
            cache_dir: Directory for caching conversions
            max_parallel: Max parallel conversions
            chunk_size: Target chunk size in characters
        """
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        # Soft-fail mode when API key is missing
        self.api_key_available = bool(self.api_key)
        if not self.api_key:
            self.logger.warning("⚠ Gemini API key not found. Converter will be disabled.")
            self.logger.warning("  Set GEMINI_API_KEY environment variable to enable Gemini conversion.")
            # Continue initialization but mark as unavailable
            self.model = model
            self.max_tokens = max_tokens
            self.cache_dir = Path(cache_dir)
            self.max_parallel = max_parallel
            self.chunk_size = chunk_size
            self.rate_limiter = None
            self.api_url = None
            self.stats = {"total_requests": 0, "total_tokens": 0, "cache_hits": 0, "total_time": 0.0}
            return
        
        self.model = model
        self.max_tokens = max_tokens
        self.cache_dir = Path(cache_dir)
        self.max_parallel = max_parallel
        self.chunk_size = chunk_size
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=max_requests_per_minute,
            max_retries=3
        )
        
        # Create cache directory
        self.cache_dir.mkdir(exist_ok=True)
        
        # API endpoint
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        # Initialize stats
        self.stats = {"total_requests": 0, "total_tokens": 0, "cache_hits": 0, "total_time": 0.0}
        
        self.logger.info(f"✓ Gemini converter initialized with rate limit: {max_requests_per_minute} requests/minute")
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'GeminiCToCSharpConverter':
        """Create converter from configuration"""
        return cls(
            api_key=config.get("api_key"),
            model=config.get("model", "gemini-2.5-pro"),
            max_tokens=config.get("max_tokens", 8192),
            cache_dir=config.get("cache_dir", ".conversion_cache"),
            max_parallel=config.get("max_parallel", 5),
            chunk_size=config.get("chunk_size", 2000),
            max_requests_per_minute=config.get("max_requests_per_minute", 1)
        )
    
    def convert(self, program: CProgram) -> str:
        """
        Convert C program to C# using Gemini API
        
        Args:
            program: CProgram to convert
            
        Returns:
            C# code string
        """
        # Check if API key is available
        if not self.api_key_available:
            self.logger.error("Cannot convert: Gemini API key not available")
            raise ValueError("Gemini API key not available. Please set GEMINI_API_KEY environment variable.")
        
        start_time = time.time()
        self.logger.info(f"Starting Gemini conversion of {program.program_id}")
        
        try:
            # Step 1: Create conversion chunks
            chunks = self._create_conversion_chunks(program)
            self.logger.info(f"Created {len(chunks)} conversion chunks")
            
            # Step 2: Process chunks with dependency resolution
            converted_chunks = self._process_chunks_with_dependencies(chunks)
            
            # Step 3: Assemble final C# code
            csharp_code = self._assemble_csharp_code(converted_chunks, program)
            
            # Step 4: Post-process and validate
            csharp_code = self._post_process_code(csharp_code)
            
            processing_time = time.time() - start_time
            self.stats["total_time"] += processing_time
            
            self.logger.info(f"✓ Conversion completed in {processing_time:.2f}s")
            self.logger.info(f"Stats: {self.stats}")
            
            return csharp_code
            
        except Exception as e:
            self.logger.error(f"Conversion failed: {e}")
            raise
    
    def _create_conversion_chunks(self, program: CProgram) -> List[ConversionChunk]:
        """Create optimal chunks for conversion"""
        chunks = []
        
        # Check if this is a multi-file project (combined program)
        is_project = ',' in program.file_path or len(program.functions) > 10
        
        # Chunk 1: Program structure and usings
        structure_chunk = ConversionChunk(
            chunk_id="program_structure",
            content=self._generate_program_structure(is_project=is_project),
            chunk_type="structure",
            dependencies=[],
            priority=10
        )
        chunks.append(structure_chunk)
        
        # Chunk 2: Defines and constants
        if program.defines:
            defines_content = self._extract_defines_content(program.defines)
            defines_chunk = ConversionChunk(
                chunk_id="defines",
                content=defines_content,
                chunk_type="define",
                dependencies=["program_structure"],
                priority=9
            )
            chunks.append(defines_chunk)
        
        # Chunk 3: Enums
        for enum in program.enums:
            enum_content = self._extract_enum_content(enum)
            enum_chunk = ConversionChunk(
                chunk_id=f"enum_{enum.name}",
                content=enum_content,
                chunk_type="enum",
                dependencies=["program_structure"],
                priority=8
            )
            chunks.append(enum_chunk)
        
        # Chunk 4: Structs
        for struct in program.structs:
            struct_content = self._extract_struct_content(struct)
            struct_chunk = ConversionChunk(
                chunk_id=f"struct_{struct.name}",
                content=struct_content,
                chunk_type="struct",
                dependencies=["program_structure"],
                priority=7
            )
            chunks.append(struct_chunk)
        
        # Chunk 5: Global variables
        if program.variables:
            globals_content = self._extract_globals_content(program.variables)
            globals_chunk = ConversionChunk(
                chunk_id="globals",
                content=globals_content,
                chunk_type="global",
                dependencies=["program_structure"],
                priority=6
            )
            chunks.append(globals_chunk)
        
        # Chunk 6: Functions (may need to split large functions)
        for func in program.functions:
            func_chunks = self._split_function_if_needed(func)
            for i, func_chunk in enumerate(func_chunks):
                chunk_id = f"func_{func.name}" + (f"_part{i+1}" if len(func_chunks) > 1 else "")
                chunks.append(ConversionChunk(
                    chunk_id=chunk_id,
                    content=func_chunk,
                    chunk_type="function",
                    dependencies=["program_structure"],
                    priority=5
                ))
        
        return chunks
    
    def _process_chunks_with_dependencies(self, chunks: List[ConversionChunk]) -> Dict[str, GeminiResponse]:
        """Process chunks respecting dependencies and using parallel processing"""
        converted_chunks = {}
        remaining_chunks = {chunk.chunk_id: chunk for chunk in chunks}
        
        # Process in dependency order with parallel execution
        while remaining_chunks:
            # Find chunks ready to process (dependencies satisfied)
            ready_chunks = []
            for chunk_id, chunk in remaining_chunks.items():
                if all(dep in converted_chunks for dep in chunk.dependencies):
                    ready_chunks.append(chunk)
            
            if not ready_chunks:
                self.logger.error("Circular dependency detected in chunks")
                break
            
            # Process ready chunks in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
                future_to_chunk = {
                    executor.submit(self._convert_chunk_with_cache, chunk): chunk
                    for chunk in ready_chunks
                }
                
                for future in concurrent.futures.as_completed(future_to_chunk):
                    chunk = future_to_chunk[future]
                    try:
                        response = future.result()
                        converted_chunks[chunk.chunk_id] = response
                        remaining_chunks.pop(chunk.chunk_id)
                        
                        if response.success:
                            self.logger.info(f"✓ Converted {chunk.chunk_id}")
                        else:
                            self.logger.warning(f"✗ Failed to convert {chunk.chunk_id}")
                            
                    except Exception as e:
                        self.logger.error(f"Error converting {chunk.chunk_id}: {e}")
                        # Create error response
                        converted_chunks[chunk.chunk_id] = GeminiResponse(
                            success=False,
                            converted_code="",
                            explanation=f"Conversion failed: {e}",
                            warnings=[],
                            tokens_used=0,
                            processing_time=0.0
                        )
                        remaining_chunks.pop(chunk.chunk_id)
        
        return converted_chunks
    
    def _convert_chunk_with_cache(self, chunk: ConversionChunk) -> GeminiResponse:
        """Convert chunk with caching"""
        # Generate cache key
        cache_key = self._generate_cache_key(chunk)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        # Check cache
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                self.stats["cache_hits"] += 1
                self.logger.debug(f"Cache hit for {chunk.chunk_id}")
                return GeminiResponse(**cached_data)
            except Exception as e:
                self.logger.warning(f"Failed to load cache for {chunk.chunk_id}: {e}")
        
        # Convert with Gemini
        response = self._convert_chunk_with_gemini(chunk)
        
        # Cache result
        if response.success:
            try:
                with open(cache_file, 'w') as f:
                    json.dump(asdict(response), f)
            except Exception as e:
                self.logger.warning(f"Failed to cache {chunk.chunk_id}: {e}")
        
        return response
    
    def _convert_chunk_with_gemini(self, chunk: ConversionChunk) -> GeminiResponse:
        """Convert single chunk using Gemini API with rate limiting and retry logic"""
        start_time = time.time()
        
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        for attempt in range(self.rate_limiter.max_retries + 1):
            try:
                # Create context-aware prompt
                prompt = self._create_conversion_prompt(chunk)
            
            # Make API request
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "maxOutputTokens": self.max_tokens,
                        "temperature": 0.1,  # Low temperature for consistent conversion
                        "topP": 0.8,
                        "topK": 40
                    }
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key
                }
                
                    # Make synchronous request
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
            
                self.stats["total_requests"] += 1
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if "candidates" in result and result["candidates"]:
                        candidate = result["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            converted_text = candidate["content"]["parts"][0]["text"]
                            
                            # Extract tokens used
                            tokens_used = 0
                            if "usageMetadata" in result:
                                tokens_used = result["usageMetadata"].get("totalTokenCount", 0)
                            
                            self.stats["total_tokens"] += tokens_used
                            
                            processing_time = time.time() - start_time
                            
                            return GeminiResponse(
                                success=True,
                                converted_code=converted_text,
                                explanation="Successfully converted with Gemini",
                                warnings=[],
                                tokens_used=tokens_used,
                                processing_time=processing_time
                            )
                
                    # Handle API error
                    error_msg = f"Gemini API error: {response.status_code} - {response.text}"
                    self.logger.error(error_msg)
                    
                    # Check if it's a quota error and handle retry
                    if self.rate_limiter.handle_quota_error(response.text, attempt):
                        continue  # Retry
                    else:
                        return GeminiResponse(
                            success=False,
                            converted_code="",
                            explanation=error_msg,
                            warnings=[],
                            tokens_used=0,
                            processing_time=time.time() - start_time
                        )
            
            except Exception as e:
                error_msg = f"Request failed: {e}"
                self.logger.error(error_msg)
                
                # For network errors, retry with exponential backoff
                if attempt < self.rate_limiter.max_retries:
                    retry_delay = min(2 ** attempt, 30)  # Max 30 seconds
                    self.logger.warning(f"Retrying in {retry_delay} seconds (attempt {attempt + 1}/{self.rate_limiter.max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    return GeminiResponse(
                        success=False,
                        converted_code="",
                        explanation=error_msg,
                        warnings=[],
                        tokens_used=0,
                        processing_time=time.time() - start_time
                    )
        
        # If we get here, all retries failed
        return GeminiResponse(
            success=False,
            converted_code="",
            explanation="All retry attempts failed",
            warnings=[],
            tokens_used=0,
            processing_time=time.time() - start_time
        )
    
    def _create_conversion_prompt(self, chunk: ConversionChunk) -> str:
        """Create context-aware prompt for conversion"""
        # Nếu loại chunk là 'harness' hoặc có yêu cầu sinh test harness:
        if hasattr(chunk, 'chunk_type') and chunk.chunk_type == 'harness':
            base_prompt = f"""
You are an expert C# test harness writer. Generate a C# test harness for the following C# method(s).
- Place the harness code in a public class named Program.
- The class must contain a public static void Main(string[] args) method.
- In Main, invoke the method(s) with representative test cases, print outputs using Console.WriteLine in the format: \"Test <name>: result = <value>\".
- Do not use external dependencies or frameworks. Do not generate function implementation in this prompt, just the harness code.

C# method skeleton(s):
{chunk.content}
"""
        else:
            # Check if this is a project-level conversion (multiple files)
            is_project = ',' in str(getattr(chunk, 'source_file', '')) or len(chunk.content) > 5000
            
            if is_project:
                base_prompt = f"""
You are an expert C to C# converter. Convert the following C PROJECT (multiple files) to idiomatic, high-accuracy C#.
- This is a MULTI-FILE PROJECT - understand the relationships and dependencies between files.
- Place ALL converted code in a SINGLE public class called ConvertedCode.
- Maintain all functions, structs, enums, and constants from ALL files in the project.
- Preserve function calls and dependencies between files correctly.
- Do NOT add a Main method or entrypoint or any test harness.
- Do not include example usage or test code or unnecessary comments.
- Use proper C# naming, pointer and struct conversion, memory management, and .NET conventions.
- Ensure all functions are public static methods in the ConvertedCode class.

C PROJECT code to convert (may contain multiple files separated by comments):
```c
{chunk.content}
```
"""
            else:
                base_prompt = f"""
You are an expert C to C# converter. Convert the following C code to idiomatic, high-accuracy C#.
- Place the converted method(s) in a public class called ConvertedCode.
- Do NOT add a Main method or entrypoint or any test harness.
- Do not include example usage or test code or unnecessary comments.
- Use proper C# naming, pointer and struct conversion, memory management, and .NET conventions.

C code to convert:
```c
{chunk.content}
```
"""
        return base_prompt
    
    def _generate_cache_key(self, chunk: ConversionChunk) -> str:
        """Generate cache key for chunk"""
        content_hash = hashlib.md5(chunk.content.encode()).hexdigest()
        return f"{chunk.chunk_type}_{chunk.chunk_id}_{content_hash}"
    
    def _split_function_if_needed(self, func: CFunction) -> List[str]:
        """Split large function into smaller chunks if needed"""
        if len(func.body) <= self.chunk_size:
            return [func.body]
        
        # Simple splitting by lines (could be improved with AST-aware splitting)
        lines = func.body.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for line in lines:
            if current_size + len(line) > self.chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = len(line)
            else:
                current_chunk.append(line)
                current_size += len(line)
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def _extract_defines_content(self, defines: List[CDefine]) -> str:
        """Extract defines as C code"""
        lines = []
        for define in defines:
            if define.is_function_macro:
                lines.append(f"#define {define.name}({define.parameters}) {define.value}")
            else:
                lines.append(f"#define {define.name} {define.value}")
        return '\n'.join(lines)
    
    def _extract_enum_content(self, enum: CEnum) -> str:
        """Extract enum as C code"""
        lines = [f"enum {enum.name} {{"]
        for name, value in enum.values.items():
            lines.append(f"    {name} = {value},")
        lines.append("};")
        return '\n'.join(lines)
    
    def _extract_struct_content(self, struct: CStruct) -> str:
        """Extract struct as C code"""
        lines = [f"struct {struct.name} {{"]
        for member in struct.members:
            type_str = member.data_type + ('*' * member.pointer_level)
            lines.append(f"    {type_str} {member.name};")
        lines.append("};")
        return '\n'.join(lines)
    
    def _extract_globals_content(self, variables: List[CVariable]) -> str:
        """Extract global variables as C code"""
        lines = []
        for var in variables:
            type_str = var.data_type + ('*' * var.pointer_level)
            init_str = f" = {var.initial_value}" if var.initial_value else ""
            static_str = "static " if var.is_static else ""
            const_str = "const " if var.is_const else ""
            lines.append(f"{static_str}{const_str}{type_str} {var.name}{init_str};")
        return '\n'.join(lines)
    
    def _generate_program_structure(self, is_project: bool = False) -> str:
        """Generate program structure template"""
        if is_project:
            return """
            // C PROJECT structure (multiple files) to convert to C#
            // This is a multi-file project - convert all files into a single ConvertedCode class
            // Maintain all dependencies and relationships between files
            """
        return """
            // C program structure to convert to C#
            // This will be wrapped in a C# class with proper using statements
            """
    
    def _assemble_csharp_code(self, converted_chunks: Dict[str, GeminiResponse], program: CProgram) -> str:
        """Assemble final C# code from converted chunks"""
        code_lines = []
        
        # Add using statements
        code_lines.extend([
            "using System;",
            "using System.Runtime.InteropServices;",
            ""
        ])
        
        # Add class declaration
        code_lines.extend([
            "public class Program",
            "{",
            ""
        ])
        
        # Add converted chunks in order
        chunk_order = [
            "program_structure",
            "defines",
            "globals"
        ]
        
        # Add enums
        for enum in program.enums:
            chunk_id = f"enum_{enum.name}"
            if chunk_id in converted_chunks and converted_chunks[chunk_id].success:
                code_lines.append("    " + converted_chunks[chunk_id].converted_code)
                code_lines.append("")
        
        # Add structs
        for struct in program.structs:
            chunk_id = f"struct_{struct.name}"
            if chunk_id in converted_chunks and converted_chunks[chunk_id].success:
                code_lines.append("    " + converted_chunks[chunk_id].converted_code)
                code_lines.append("")
        
        # Add functions
        for func in program.functions:
            chunk_id = f"func_{func.name}"
            if chunk_id in converted_chunks and converted_chunks[chunk_id].success:
                code_lines.append("    " + converted_chunks[chunk_id].converted_code)
                code_lines.append("")
        
        # Close class
        code_lines.append("}")
        
        return '\n'.join(code_lines)
    
    def _post_process_code(self, code: str) -> str:
        """Post-process generated C# code"""
        # Remove duplicate using statements
        lines = code.split('\n')
        seen_usings = set()
        filtered_lines = []
        
        for line in lines:
            if line.strip().startswith('using '):
                if line.strip() not in seen_usings:
                    seen_usings.add(line.strip())
                    filtered_lines.append(line)
            else:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get conversion statistics"""
        return self.stats.copy()
    
    def clear_cache(self) -> None:
        """Clear conversion cache"""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.logger.info("Cache cleared")
