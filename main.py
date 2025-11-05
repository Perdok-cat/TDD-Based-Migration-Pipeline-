#!/usr/bin/env python3
"""
C to C# Migration Pipeline - Main Entry Point
"""
import sys
import logging
import yaml
from pathlib import Path    
from typing import Optional, Dict, Any
import click
from rich.console import Console
from rich.logging import RichHandler

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestrator.migration_orchestrator import MigrationOrchestrator
from src.core.models.dependency_graph import DependencyGraph

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger(__name__)
console = Console()


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"✓ Loaded configuration from: {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return {}


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    C to C# Migration Pipeline - TDD-Based System
    
    A Python-based tool to automatically migrate C code to C# with
    comprehensive testing and validation.
    """
    pass


@cli.command()
@click.option(
    '--input', '-i',
    required=True,
    type=click.Path(exists=True),
    help='Input directory containing C source files or single C file'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    default='output/converted',
    help='Output directory for converted C# files'
)
@click.option(
    '--config', '-c',
    type=click.Path(exists=True),
    help='Path to configuration YAML file'
)
@click.option(
    '--max-retries',
    type=int,
    default=3,
    help='Maximum number of retry attempts per component'
)
@click.option(
    '--parallel/--sequential',
    default=False,
    help='Enable parallel processing of independent components'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging'
)
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug mode with detailed logging'
)
def migrate(
    input: str,
    output: str,
    config: Optional[str],
    max_retries: int,
    parallel: bool,
    verbose: bool,
    debug: bool
):
    """
    Migrate C code to C# using TDD-based approach.
    
    This command follows the migration workflow:
    1. Parse C programs and build dependency graph
    2. Select components ready to convert
    3. Generate test cases
    4. Run C tests to get baseline outputs
    5. Convert C to C#
    6. Run C# tests
    7. Validate outputs (C vs C#)
    8. Repeat until all components converted
    9. Generate migration report
    
    Example:
        python main.py migrate -i examples/c_samples -o output/converted
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif verbose:
        logging.getLogger().setLevel(logging.INFO)
    
    console.print("\n[bold cyan]C to C# Migration Pipeline[/bold cyan]")
    console.print(f"[dim]Input: {input}[/dim]")
    console.print(f"[dim]Output: {output}[/dim]\n")
    
    try:
        # Load base config from YAML if provided, otherwise use defaults
        if config:
            yaml_config = load_config_file(config)
        else:
            # Try to load default config.yaml
            default_config = Path(__file__).parent / "config" / "config.yaml"
            if default_config.exists():
                yaml_config = load_config_file(str(default_config))
            else:
                yaml_config = {}
        
        # Build migration config by merging YAML config with CLI options
        migration_config = {
            'max_retries': max_retries,
            'parallel_execution': parallel,
            'output_dir': output,
            'verbose': verbose or debug
        }
        
        # Merge converter config from YAML (including Gemini settings)
        if 'converter' in yaml_config:
            migration_config['converter'] = yaml_config['converter']
            logger.info(f"✓ Loaded converter config with keys: {list(yaml_config['converter'].keys())}")
            # Extract Gemini API key from config
            if 'gemini' in yaml_config['converter']:
                gemini_config = yaml_config['converter']['gemini']
                logger.info(f"✓ Loaded gemini config with keys: {list(gemini_config.keys())}")
                # Check if api_key_env is actually the API key (not env var name)
                api_key_value = gemini_config.get('api_key_env', '')
                logger.info(f"✓ API key from config: {api_key_value[:15]}... (length: {len(api_key_value)})")
                if api_key_value and api_key_value.startswith('AIza'):
                    # It's an actual API key, use it directly
                    migration_config['converter']['gemini']['gemini_api_key'] = api_key_value
                    logger.info("✓ Using Gemini API key from config file")
        
        # Create orchestrator
        orchestrator = MigrationOrchestrator(config=migration_config)
        
        # Run migration
        report = orchestrator.migrate_all(
            input_dir=input,
            output_dir=output
        )
        
        # Display summary
        console.print("\n[bold green]Migration Complete![/bold green]")
        console.print(report.get_summary())
        
        # Exit code based on success
        if report.failed_programs == 0:
            sys.exit(0)
        else:
            console.print(f"\n[yellow]Warning: {report.failed_programs} programs failed to convert[/yellow]")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        if debug:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.option(
    '--input', '-i',
    required=True,
    type=click.Path(exists=True),
    help='Input directory containing C source files'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    help='Output file for dependency graph (optional)'
)
@click.option(
    '--visualize', '-v',
    is_flag=True,
    help='Print visual representation of dependency graph'
)
def analyze(input: str, output: Optional[str], visualize: bool):
    """
    Analyze dependencies between C programs.
    
    This command only performs dependency analysis without conversion.
    Useful for understanding the structure and identifying circular dependencies.
    
    Example:
        python main.py analyze -i examples/c_samples --visualize
    """
    console.print("\n[bold cyan]Dependency Analysis[/bold cyan]\n")
    
    try:
        # TODO: Implement dependency analysis
        console.print(f"[dim]Analyzing: {input}[/dim]\n")
        
        # Placeholder
        console.print("[yellow]Dependency analyzer not yet fully implemented[/yellow]")
        console.print("Creating demo dependency graph...\n")
        
        # Demo graph
        graph = DependencyGraph()
        graph.add_node("module_a", [])
        graph.add_node("module_b", ["module_a"])
        graph.add_node("module_c", ["module_a", "module_b"])
        
        stats = graph.get_statistics()
        
        console.print(f"[green]Found {stats['total_programs']} programs[/green]")
        console.print(f"[green]Total dependencies: {stats['total_dependencies']}[/green]")
        
        if stats['circular_dependencies'] > 0:
            console.print(f"\n[red]⚠ {stats['circular_dependencies']} circular dependencies detected![/red]")
            for cycle in stats['cycles']:
                console.print(f"  Cycle: {' → '.join(cycle)}")
        else:
            console.print("\n[green]✓ No circular dependencies found[/green]")
        
        if visualize:
            console.print("\n[bold]Dependency Graph:[/bold]")
            console.print(graph.visualize())
        
        # Try to get conversion order
        try:
            order = graph.get_conversion_order()
            console.print(f"\n[bold]Recommended Conversion Order:[/bold]")
            for idx, program_id in enumerate(order, 1):
                console.print(f"  {idx}. {program_id}")
        except ValueError as e:
            console.print(f"\n[red]Cannot determine conversion order: {e}[/red]")
    
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    '--input', '-i',
    required=True,
    type=click.Path(exists=True),
    help='Input directory or file containing migration results'
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    default='output/reports',
    help='Output directory for reports'
)
@click.option(
    '--format', '-f',
    type=click.Choice(['html', 'json', 'markdown', 'all']),
    default='all',
    help='Report format'
)
def report(input: str, output: str, format: str):
    """
    Generate migration report from previous run.
    
    Example:
        python main.py report -i output/test_results -o output/reports --format html
    """
    console.print("\n[bold cyan]Generating Migration Report[/bold cyan]\n")
    
    try:
        console.print(f"[dim]Input: {input}[/dim]")
        console.print(f"[dim]Output: {output}[/dim]")
        console.print(f"[dim]Format: {format}[/dim]\n")
        
        # TODO: Implement report generation
        console.print("[yellow]Report generator not yet fully implemented[/yellow]")
        
        Path(output).mkdir(parents=True, exist_ok=True)
        
        console.print(f"\n[green]✓ Report would be generated at: {output}[/green]")
    
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
def info():
    """Display system information and configuration."""
    console.print("\n[bold cyan]System Information[/bold cyan]\n")
    
    console.print(f"[green]Python Version:[/green] {sys.version}")
    console.print(f"[green]Platform:[/green] {sys.platform}")
    
    # Check for required tools
    console.print("\n[bold]Required Tools:[/bold]")
    
    import shutil
    tools = {
        'gcc': 'C compiler',
        'csc': 'C# compiler (Mono)',
        'dotnet': 'C# compiler (.NET)',
    }
    
    for tool, description in tools.items():
        if shutil.which(tool):
            console.print(f"  [green]✓[/green] {tool} ({description})")
        else:
            console.print(f"  [red]✗[/red] {tool} ({description}) - NOT FOUND")
    
    console.print("\n")


if __name__ == '__main__':
    cli()

