# Use an official Ubuntu image as the base
FROM ubuntu:22.04

# Install dependencies
RUN apt update && apt install -y \
    build-essential \
    libncurses-dev \
    bison \
    flex \
    libssl-dev \
    libelf-dev \
    python3 \
    python3-pip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install requests colorama

# Copy the script into the container
COPY kernel-config.py /usr/local/bin/kernel-config.py
RUN chmod +x /usr/local/bin/kernel-config.py

# Set the working directory
WORKDIR /workspace

# Default command
CMD ["/usr/local/bin/kernel-config.py", "--help"]
