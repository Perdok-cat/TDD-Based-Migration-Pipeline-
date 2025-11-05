"""
Adapter để tích hợp Gemini converter vào hệ thống hiện tại
"""
import logging
from typing import Optional, Dict, Any

from ..core.models.c_program import CProgram
from .c_to_csharp_converter import CToCSharpConverter
from .gemini_c_to_csharp_converter import GeminiCToCSharpConverter


class HybridCToCSharpConverter:
    """
    Hybrid converter sử dụng cả rule-based và Gemini API
    
    Chiến lược:
    1. Sử dụng Gemini cho các phần phức tạp (functions, structs)
    2. Sử dụng rule-based cho các phần đơn giản (defines, enums)
    3. Fallback mechanism khi Gemini không available
    """
    
    def __init__(
        self,
        use_gemini: bool = True,
        gemini_api_key: Optional[str] = None,
        fallback_to_rules: bool = True,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize hybrid converter
        
        Args:
            use_gemini: Enable Gemini conversion
            gemini_api_key: Gemini API key
            fallback_to_rules: Fallback to rule-based when Gemini fails
        """
        self.logger = logging.getLogger(__name__)
        self.use_gemini = use_gemini
        self.fallback_to_rules = fallback_to_rules
        self.config = config or {}
        
        # Debug logging
        self.logger.debug(f"HybridConverter init - use_gemini: {use_gemini}")
        self.logger.debug(f"HybridConverter init - gemini_api_key param: {gemini_api_key[:10] if gemini_api_key else None}...")
        self.logger.debug(f"HybridConverter init - config keys: {list(self.config.keys())}")
        
        # Initialize converters
        self.rule_converter = CToCSharpConverter()
        self.gemini_converter = None
        
        if use_gemini:
            try:
                # Create Gemini converter with rate limiting from config
                gemini_config = self.config.get("gemini", {})
                rate_config = gemini_config.get("rate_limiting", {})
                
                # Get API key from config or parameter
                api_key = gemini_api_key or gemini_config.get("api_key_env")
                self.logger.info(f"api key : {api_key}")
                self.logger.info(f"rate_config: {rate_config}")
                
                self.gemini_converter = GeminiCToCSharpConverter(
                    api_key=api_key,
                    model=gemini_config.get("model", "gemini-2.5-pro"),
                    max_tokens=gemini_config.get("max_tokens", 8192),
                    max_parallel=gemini_config.get("max_parallel", 3),
                    chunk_size=gemini_config.get("chunk_size", 1500),
                    max_requests_per_minute=rate_config.get("max_requests_per_minute", 1)
                )
                
                # Check if API key is available
                if not self.gemini_converter.api_key_available:
                    self.logger.warning("✗ Gemini API key not available, disabling Gemini conversion")
                    self.gemini_converter = None
                    self.use_gemini = False
                else:
                    self.logger.info("✓ Gemini converter initialized with rate limiting")
            except Exception as e:
                self.logger.warning(f"✗ Gemini converter failed to initialize: {e}")
                self.gemini_converter = None
                self.use_gemini = False
    
    def convert(self, program: CProgram) -> str:
        """
        Convert C program to C# using hybrid approach
        
        Args:
            program: CProgram to convert
            
        Returns:
            C# code string
        """
        self.logger.info(f"Starting hybrid conversion of {program.program_id}") 
        
        try:
            # Strategy 1: Try Gemini first if available
            if self.use_gemini and self.gemini_converter:
                try:
                    self.logger.info("Attempting Gemini conversion...")
                    csharp_code = self.gemini_converter.convert(program)
                    
                    # Validate Gemini output
                    if self._validate_gemini_output(csharp_code):
                        self.logger.info("✓ Gemini conversion successful")
                        return csharp_code
                    else:
                        self.logger.warning("✗ Gemini output validation failed")
                        
                except ValueError as e:
                    # API key not available or other value errors
                    self.logger.warning(f"✗ Gemini conversion not available: {e}")
                    if self.fallback_to_rules:
                        self.logger.info("→ Falling back to rule-based conversion")
                except Exception as e:
                    self.logger.warning(f"✗ Gemini conversion failed: {e}")
                    if self.fallback_to_rules:
                        self.logger.info("→ Falling back to rule-based conversion")
            
            # Strategy 2: Fallback to rule-based
            if self.fallback_to_rules:
                self.logger.info("Falling back to rule-based conversion...")
                return self.rule_converter.convert(program)
            
            # Strategy 3: Emergency fallback - basic conversion
            self.logger.warning("Using emergency fallback conversion")
            return self._emergency_conversion(program)
            
        except Exception as e:
            self.logger.error(f"All conversion strategies failed: {e}")
            return self._emergency_conversion(program)
    
    def _validate_gemini_output(self, code: str) -> bool:
        """Validate Gemini conversion output"""
        if not code or len(code.strip()) < 50:
            return False
        
        # Check for basic C# syntax
        required_elements = [
            "using System",
            "public class",
            "}"
        ]
        
        for element in required_elements:
            if element not in code:
                return False
        
        return True
    
    def _emergency_conversion(self, program: CProgram) -> str:
        """Emergency fallback conversion"""
        lines = [
            "using System;",
            "",
            "public class Program",
            "{",
            "    // Emergency conversion - manual review required",
            ""
        ]
        
        # Add basic function stubs
        for func in program.functions:
            params = ', '.join(f"{p.data_type} {p.name}" for p in func.parameters)
            lines.append(f"    public static {func.return_type} {func.name}({params})")
            lines.append("    {")
            lines.append("        // TODO: Implement conversion")
            lines.append("        throw new NotImplementedException();")
            lines.append("    }")
            lines.append("")
        
        lines.append("}")
        
        return '\n'.join(lines)
    
    def get_conversion_stats(self) -> Dict[str, Any]:
        """Get conversion statistics"""
        stats = {
            "converter_type": "hybrid",
            "gemini_enabled": self.use_gemini,
            "fallback_enabled": self.fallback_to_rules
        }
        
        if self.gemini_converter:
            stats["gemini_stats"] = self.gemini_converter.get_stats()
        
        return stats


# Factory function để tạo converter dựa trên config
def create_converter(config: Optional[Dict[str, Any]] = None) -> HybridCToCSharpConverter:
    """
    Factory function để tạo converter
    
    Args:
        config: Configuration dict with nested structure from YAML:
            {
                "gemini": {
                    "enabled": bool,
                    "gemini_api_key": str,
                    ...
                },
                "fallback_to_rules": bool
            }
    
    Returns:
        HybridCToCSharpConverter instance
    """
    config = config or {}
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"create_converter - config keys: {list(config.keys())}")
    
    # Check if config has nested gemini structure (from YAML)
    gemini_config = config.get("gemini", {})
    logger.info(f"create_converter - gemini_config keys: {list(gemini_config.keys())}")
    
    use_gemini = gemini_config.get("enabled", True) if gemini_config else config.get("use_gemini", True)
    # Try multiple possible key names for API key
    gemini_api_key = (gemini_config.get("gemini_api_key") or 
                      gemini_config.get("api_key_env") or 
                      config.get("gemini_api_key"))
    
    logger.info(f"create_converter - use_gemini: {use_gemini}")
    logger.info(f"create_converter - API key found: {bool(gemini_api_key)} (length: {len(gemini_api_key) if gemini_api_key else 0})")
    
    fallback_to_rules = gemini_config.get("fallback_to_rules", True) if gemini_config else config.get("fallback_to_rules", True)
    
    return HybridCToCSharpConverter(
        use_gemini=use_gemini,
        gemini_api_key=gemini_api_key,
        fallback_to_rules=fallback_to_rules,
        config=config  # Pass full config to HybridConverter
    )
