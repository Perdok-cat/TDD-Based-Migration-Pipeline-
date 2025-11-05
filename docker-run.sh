#!/bin/bash

# Script để chạy C to C# Migration System với Docker
# Cách dùng: ./docker-run.sh [command] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🐳 $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker chưa được cài đặt!"
        echo "Vui lòng cài đặt Docker từ: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose chưa được cài đặt!"
        echo "Vui lòng cài đặt Docker Compose từ: https://docs.docker.com/compose/install/"
        exit 1
    fi
}

# Check if Docker daemon is running
check_docker_running() {
    if ! docker info &> /dev/null; then
        print_error "Docker daemon không chạy!"
        echo "Khởi động Docker bằng lệnh: sudo systemctl start docker"
        echo "Hoặc mở Docker Desktop nếu bạn dùng Docker Desktop"
        exit 1
    fi
}

# Show help
show_help() {
    print_header "C to C# Migration System - Docker Runner"
    echo ""
    echo "Cách dùng: ./docker-run.sh [command] [options]"
    echo ""
    echo "Commands:"
    echo "  build              Build Docker image"
    echo "  migrate [INPUT]    Run migration (mặc định: examples/test_project)"
    echo "  analyze [INPUT]    Analyze dependencies"
    echo "  info               Show system information"
    echo "  shell              Open bash shell in container"
    echo "  clean              Remove containers and volumes"
    echo "  rebuild            Rebuild image from scratch"
    echo "  quickstart         Quick start demo"
    echo "  help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./docker-run.sh build"
    echo "  ./docker-run.sh migrate"
    echo "  ./docker-run.sh migrate examples/test_project/sum.c"
    echo "  ./docker-run.sh analyze examples/test_project"
    echo "  ./docker-run.sh shell"
    echo ""
}

# Build Docker image
build_image() {
    print_header "Building Docker Image"
    print_info "Đang build Docker image... (lần đầu có thể mất 10-15 phút)"
    
    docker-compose build
    
    print_success "Build thành công!"
}

# Run migration
run_migrate() {
    local input=${1:-examples/test_project}
    local output=${2:-output/converted}
    
    print_header "Running Migration"
    print_info "Input: $input"
    print_info "Output: $output"
    echo ""
    
    docker-compose run --rm migration-system python3 main.py migrate \
        -i "$input" \
        -o "$output" \
        --verbose
    
    print_success "Migration hoàn thành!"
    print_info "Xem kết quả tại: $output/"
}

# Analyze dependencies
run_analyze() {
    local input=${1:-examples/test_project}
    
    print_header "Analyzing Dependencies"
    print_info "Input: $input"
    echo ""
    
    docker-compose run --rm migration-system python3 main.py analyze \
        -i "$input" \
        --visualize
}

# Show system info
show_info() {
    print_header "System Information"
    
    docker-compose run --rm migration-system python3 main.py info
}

# Open shell
open_shell() {
    print_header "Opening Shell"
    print_info "Đang mở bash shell trong container..."
    print_info "Gõ 'exit' để thoát"
    echo ""
    
    docker-compose run --rm migration-system bash
}

# Clean up
clean_up() {
    print_header "Cleaning Up"
    print_warning "Sẽ xóa containers và volumes"
    
    read -p "Bạn có chắc chắn? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        print_success "Đã dọn dẹp!"
    else
        print_info "Hủy bỏ"
    fi
}

# Rebuild from scratch
rebuild_image() {
    print_header "Rebuilding from Scratch"
    print_info "Đang rebuild image (không dùng cache)..."
    
    docker-compose build --no-cache
    
    print_success "Rebuild thành công!"
}

# Quick start demo
quick_start() {
    print_header "Quick Start Demo"
    
    print_info "Bước 1/3: Building Docker image..."
    build_image
    echo ""
    
    print_info "Bước 2/3: Running migration..."
    run_migrate
    echo ""
    
    print_info "Bước 3/3: Showing results..."
    echo ""
    ls -lh output/converted/
    echo ""
    
    print_success "Quick start hoàn thành!"
    print_info "Xem code C# đã convert:"
    echo "    cat output/converted/*.cs"
}

# Main script
main() {
    # Check Docker installation
    check_docker
    check_docker_running
    
    # Parse command
    case "${1:-help}" in
        build)
            build_image
            ;;
        migrate)
            run_migrate "$2" "$3"
            ;;
        analyze)
            run_analyze "$2"
            ;;
        info)
            show_info
            ;;
        shell)
            open_shell
            ;;
        clean)
            clean_up
            ;;
        rebuild)
            rebuild_image
            ;;
        quickstart)
            quick_start
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Lệnh không hợp lệ: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

