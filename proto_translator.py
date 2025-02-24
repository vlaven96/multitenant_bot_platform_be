import os
import subprocess

# Step 1: Find all .proto files
proto_files = [
    os.path.join(root, file)
    for root, _, files in os.walk("./app/protos")
    for file in files if file.endswith(".proto")
]

# Check if we found any .proto files
if not proto_files:
    print("No .proto files found. Exiting...")
    exit(1)

# Step 2: Compile each .proto file in its own directory
print("Compiling .proto files...")

for proto_file in proto_files:
    proto_dir = os.path.dirname(proto_file)  # Get directory where the .proto file exists

    protoc_cmd = [
        "python", "-m", "grpc_tools.protoc",
        f"-I{proto_dir}",  # Include directory of the .proto file
        f"--python_out={proto_dir}",  # Output Python files in the same directory
        f"--grpc_python_out={proto_dir}",  # Output gRPC Python files in the same directory
        proto_file  # Process this specific .proto file
    ]

    try:
        subprocess.run(protoc_cmd, check=True)
        print(f"Compiled: {proto_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error compiling {proto_file}: {e}")

# Step 3: Ensure __init__.py files exist in each directory containing .proto files
print("Ensuring __init__.py files exist...")

for proto_file in proto_files:
    proto_dir = os.path.dirname(proto_file)
    init_file = os.path.join(proto_dir, "__init__.py")

    if not os.path.exists(init_file):
        open(init_file, 'a').close()  # Create an empty __init__.py file
        print(f"Created: {init_file}")

print("Protobuf files compiled successfully and __init__.py files added!")
