# Linux Kernel Build Script for Firecracker

This script automates the process of downloading, configuring, and building a Linux kernel. It supports custom kernel configurations via a JSON file and allows the use of a predefined `.config` file.

---

## **Features**
- **Incremental Builds**: Reuse previously compiled object files and avoid cleaning the build directory unless explicitly requested.
- **Verbose Mode**: Enable detailed logging for debugging purposes.
- **Automatic Dependency Installation**: Detect the Linux distribution and install dependencies using the appropriate package manager.
- **Docker Integration**: Build the kernel in a containerized environment for consistent results.
- **Colorized Output**: Use colored logging for better readability.

---

## **Prerequisites**
- Python 3.x
- `requests` library (install via `pip install requests`)
- `colorama` library (install via `pip install colorama`)
- Build tools (e.g., `build-essential`, `libncurses-dev`, etc.)

---

## **Usage**

### **Script Name**
The script is named `kernel-config.py`.

### **Configuration File**
The configuration file is named `config.json`. It should contain the kernel version and additional configuration options.

Example `config.json`:
```json
{
    "KERNEL_VERSION": "5.15.0",
    "KERNEL_CONFIG": {
        "CONFIG_VIRTIO": "y",
        "CONFIG_NET_9P": "n"
    }
}
