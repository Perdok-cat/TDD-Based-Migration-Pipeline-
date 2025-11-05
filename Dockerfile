FROM klee/klee:3.0
USER root

# Sửa lỗi NO_PUBKEY cho apt.kitware.com và cài .NET 8 SDK
RUN set -eux; \
    apt-get update && apt-get install -y --no-install-recommends wget gpg ca-certificates; \
    # Cài key của Kitware theo chuẩn keyring
    wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc \
      | gpg --dearmor -o /usr/share/keyrings/kitware-archive-keyring.gpg; \
    echo "deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ jammy main" \
      > /etc/apt/sources.list.d/kitware.list; \
    # Thêm repo Microsoft cho .NET
    wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O /tmp/msprod.deb; \
    dpkg -i /tmp/msprod.deb; \
    apt-get update; \
    apt-get install -y --no-install-recommends dotnet-sdk-8.0; \
    rm -rf /var/lib/apt/lists/* /tmp/msprod.deb

# Cài đặt Python và pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Tạo thư mục làm việc
WORKDIR /app

# Copy requirements.txt và cài đặt dependencies Python
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy toàn bộ source code vào container
COPY . .

# Tạo thư mục output
RUN mkdir -p output/converted output/reports output/test_results output/logs

# Đổi quyền sở hữu cho user klee
RUN chown -R klee:klee /app

# Chuyển về user klee (non-root user)
USER klee

# Set environment variables
ENV PYTHONPATH=/app
ENV PATH=/app:$PATH

# Mặc định chạy help command
CMD ["python3", "main.py", "--help"]
