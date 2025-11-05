# 🐳 Hướng dẫn chạy dự án với Docker

## 📋 Yêu cầu hệ thống

- Docker Engine 20.10+ hoặc Docker Desktop
- Docker Compose 2.0+
- Ít nhất 4GB RAM available cho Docker
- Ít nhất 10GB disk space

## 🚀 Cách 1: Sử dụng Docker Compose (Khuyên dùng)

### Bước 1: Build Docker image

```bash
docker-compose build
```

Lệnh này sẽ:
- Tải base image `klee/klee:3.0`
- Cài đặt .NET SDK 8.0
- Cài đặt Python 3 và các dependencies
- Copy source code vào container
- Tạo các thư mục output cần thiết

### Bước 2: Chạy container

#### a) Chạy với command mặc định (hiển thị help)
```bash
docker-compose run --rm migration-system
```

#### b) Chạy migration với ví dụ có sẵn
```bash
docker-compose run --rm migration-system python3 main.py migrate \
  -i examples/test_project \
  -o output/converted \
  -c config/config.yaml
```

#### c) Chạy với verbose mode để xem chi tiết
```bash
docker-compose run --rm migration-system python3 main.py migrate \
  -i examples/test_project \
  -o output/converted \
  --verbose
```

#### d) Chạy với debug mode
```bash
docker-compose run --rm migration-system python3 main.py migrate \
  -i examples/test_project \
  -o output/converted \
  --debug
```

#### e) Phân tích dependencies
```bash
docker-compose run --rm migration-system python3 main.py analyze \
  -i examples/test_project \
  --visualize
```

#### f) Xem thông tin hệ thống
```bash
docker-compose run --rm migration-system python3 main.py info
```

### Bước 3: Chạy container ở chế độ interactive

Nếu muốn vào bên trong container để thực hiện nhiều lệnh:

```bash
docker-compose run --rm migration-system bash
```

Sau đó có thể chạy các lệnh bên trong:

```bash
# Xem danh sách file
ls -la

# Chạy migration
python3 main.py migrate -i examples/test_project -o output/converted

# Xem kết quả
ls -la output/converted/

# Xem code C# đã convert
cat output/converted/*.cs

# Thoát container
exit
```

## 🔧 Cách 2: Sử dụng Docker commands trực tiếp

### Build image
```bash
docker build -t c-to-csharp-migration .
```

### Chạy container
```bash
docker run --rm \
  -v $(pwd)/examples:/app/examples \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/config:/app/config \
  c-to-csharp-migration \
  python3 main.py migrate -i examples/test_project -o output/converted
```

### Chạy interactive mode
```bash
docker run --rm -it \
  -v $(pwd)/examples:/app/examples \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/config:/app/config \
  c-to-csharp-migration \
  bash
```

## 📂 Volumes được mount

Các thư mục sau được mount từ host vào container:

- `./examples` → `/app/examples` - Chứa file C input
- `./output` → `/app/output` - Chứa kết quả output
- `./config` → `/app/config` - Chứa file cấu hình
- `./generated_csharp` → `/app/generated_csharp` - Chứa code C# đã generate

## 📝 Ví dụ thực tế

### Ví dụ 1: Convert file C đơn giản

1. Tạo file C mới trong `examples/test_project/hello.c`:

```c
#include <stdio.h>

int main() {
    printf("Hello, World!\n");
    return 0;
}
```

2. Chạy migration:

```bash
docker-compose run --rm migration-system python3 main.py migrate \
  -i examples/test_project/hello.c \
  -o output/converted
```

3. Xem kết quả:

```bash
cat output/converted/*.cs
```

### Ví dụ 2: Convert project với nhiều file

```bash
docker-compose run --rm migration-system python3 main.py migrate \
  -i examples/test_project \
  -o output/converted \
  --parallel \
  --verbose
```

### Ví dụ 3: Chạy với custom config

1. Chỉnh sửa `config/config.yaml`

2. Chạy migration:

```bash
docker-compose run --rm migration-system python3 main.py migrate \
  -i examples/test_project \
  -o output/converted \
  -c config/config.yaml
```

## 🛠️ Troubleshooting

### Lỗi: "Cannot connect to the Docker daemon"

**Giải pháp:**
```bash
# Khởi động Docker service
sudo systemctl start docker

# Hoặc với Docker Desktop, mở ứng dụng Docker Desktop
```

### Lỗi: "Permission denied" khi access volume

**Giải pháp:**
```bash
# Thay đổi quyền của thư mục output
chmod -R 777 output/

# Hoặc chạy với user hiện tại
docker-compose run --rm --user $(id -u):$(id -g) migration-system python3 main.py migrate ...
```

### Lỗi: "No space left on device"

**Giải pháp:**
```bash
# Xóa các container và image không dùng
docker system prune -a

# Xóa volumes không dùng
docker volume prune
```

### Container build quá lâu

**Giải pháp:**
- Lần đầu build sẽ mất 10-15 phút vì phải tải base image và cài đặt dependencies
- Các lần build sau sẽ nhanh hơn nhờ Docker cache
- Có thể tăng tốc bằng cách sử dụng Docker BuildKit:

```bash
DOCKER_BUILDKIT=1 docker-compose build
```

### Muốn xem log chi tiết

```bash
# Chạy với --verbose flag
docker-compose run --rm migration-system python3 main.py migrate \
  -i examples/test_project \
  -o output/converted \
  --verbose

# Hoặc xem log file
docker-compose run --rm migration-system cat output/logs/migration.log
```

## 🔍 Kiểm tra môi trường trong Container

Chạy các lệnh sau để kiểm tra:

```bash
# Vào container
docker-compose run --rm migration-system bash

# Kiểm tra Python
python3 --version

# Kiểm tra .NET
dotnet --version

# Kiểm tra GCC
gcc --version

# Kiểm tra KLEE
klee --version

# Kiểm tra Python packages
pip3 list

# Thoát
exit
```

## 🧹 Dọn dẹp

### Xóa container đã dừng
```bash
docker-compose down
```

### Xóa container và volumes
```bash
docker-compose down -v
```

### Xóa image
```bash
docker rmi c-to-csharp-migration
```

### Xóa tất cả (cẩn thận!)
```bash
docker-compose down -v --rmi all
```

## 📊 Monitoring

### Xem resource usage của container
```bash
docker stats
```

### Xem logs real-time
```bash
docker-compose logs -f migration-system
```

## 💡 Tips & Best Practices

1. **Sử dụng .dockerignore**: Tránh copy các file không cần thiết vào image
2. **Mount volumes**: Luôn mount volumes để dữ liệu không bị mất khi container stop
3. **Use --rm flag**: Tự động xóa container sau khi chạy xong
4. **Rebuild khi cần**: Nếu thay đổi requirements.txt hoặc Dockerfile, cần rebuild:
   ```bash
   docker-compose build --no-cache
   ```
5. **Backup output**: Định kỳ backup thư mục output ra ngoài

## 🔐 Security

- Container chạy với user `klee` (non-root) để tăng security
- Không mount thư mục nhạy cảm vào container
- Không hard-code API keys trong Dockerfile
- Sử dụng environment variables cho sensitive data:

```bash
docker-compose run --rm \
  -e GEMINI_API_KEY=your-api-key \
  migration-system \
  python3 main.py migrate ...
```

## 📚 Tài liệu tham khảo

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [KLEE Docker Documentation](https://klee.github.io/docker/)
- [.NET in Docker](https://learn.microsoft.com/en-us/dotnet/core/docker/introduction)

## 🆘 Cần trợ giúp?

Nếu gặp vấn đề, hãy:

1. Kiểm tra logs: `docker-compose logs`
2. Vào container để debug: `docker-compose run --rm migration-system bash`
3. Rebuild image: `docker-compose build --no-cache`
4. Xem issue tracker trong repository
5. Tạo issue mới với log chi tiết

