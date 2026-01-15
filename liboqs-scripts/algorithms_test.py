#!/usr/bin/env python3
import datetime
import glob
import subprocess
import oqs
import os
import psutil
import sys
import time
import tracemalloc
from pathlib import Path

# Parameters
create_random_files = False
number_of_files = 5
size_of_files_in_mb = 100
file_extension = "bin"


def get_rpi_model():
    """Get Raspberry Pi model"""
    try:
        result = subprocess.check_output(['cat', '/proc/device-tree/model']).decode().strip()
        return f"rpi_{result.split()[2]}"  # Return model number
    except:
        return "Unknown"
    
def create_random_files(filename, num_files, size_in_mb=100, extension="bin"):
    for i in range(num_files):
        with open(f"{Path(__file__).parent / f'{Path(filename).stem}_{i}.{extension}'}", "wb") as f:
            f.write(os.urandom(size_in_mb * 1024 * 1024))

def signing(alg, files):
    # Create signer and verifier
    with oqs.Signature(alg) as signer, oqs.Signature(alg) as verifier:
        # Signer generates its keypair
        signer_public_key = signer.generate_keypair()

        # Sign each file in the list
        for filename in files:
            with open(filename, 'rb') as file:
                bytes = file.read()

                # Signer signs the message
                signature = signer.sign(bytes)

                # Verifier verifies the signature
                is_valid = verifier.verify(bytes, signature, signer_public_key)
                print(f"Valid signature ({Path(filename).name})? {is_valid}\t|\t")


if __name__ == "__main__":
    # List of digital signing algorithms to be tested in this script
    sigalgs = ["Falcon-512", "Falcon-1024", "ML-DSA-44", "ML-DSA-65", "ML-DSA-87", "SPHINCS+-SHA2-128f-simple", "SPHINCS+-SHA2-192f-simple", "SPHINCS+-SHA2-256f-simple",
               "SLH_DSA_PURE_SHA2_128F", "SLH_DSA_PURE_SHA2_192F", "SLH_DSA_PURE_SHA2_256F", "SLH_DSA_PURE_SHAKE_128F", "SLH_DSA_PURE_SHAKE_192F", "SLH_DSA_PURE_SHAKE_256F",
               "cross-rsdp-128-balanced", "cross-rsdp-128-fast", "cross-rsdp-128-small", "cross-rsdp-192-balanced", "cross-rsdp-192-fast", "cross-rsdp-192-small",
               "cross-rsdp-256-balanced", "cross-rsdp-256-fast", "cross-rsdp-256-small", "MAYO-1", "MAYO-2", "MAYO-3", "MAYO-5", "SNOVA_24_5_4", "SNOVA_56_25_2", "SNOVA_60_10_4",
               "OV-Is", "OV-III", "OV-V"]

    # Output .csv file
    rpi_model = get_rpi_model()
    output_csv = f"signing_benchmark_{rpi_model}.csv"
    f = open(Path(__file__).parent / output_csv, 'w')
    # Write CSV header
    f.write("Algorithm,Start Time,End Time,Execution Time (s),Memory Used (MB),CPU Usage (%),Read Bytes,Write Bytes\n")

    if create_random_files:
        # Create random files for testing
        create_random_files("testfile", number_of_files, size_of_files_in_mb, file_extension)

    # Grab all files with the above extension type from the directory passed as a cmd line arg
    #files = glob.glob(f"{sys.argv[1]}/*.{file_extension}")
    files = glob.glob(f"{Path(__file__).parent}/*.{file_extension}")

    if len(files) == 0:
        print(f"No files with .{file_extension} extension found in the specified directory.")
        sys.exit(1)

    # Get process id
    current_process = psutil.Process(os.getpid())
    _ = current_process.cpu_percent()

    for alg in sigalgs:
        print(f"Algorithm: {alg}\t|\t")
        line = f"{alg},"

        # Start timer, memory tracing, and i/o tracking
        start_time = time.perf_counter()
        start_date_time = datetime.datetime.now()
        line += f"{start_date_time}"
        tracemalloc.start()
        initial_io_info = current_process.io_counters()
        initial_cpu_times = current_process.cpu_times()

        signing(alg, files)

        # End timer
        end_time = time.perf_counter()
        end_date_time = datetime.datetime.now()
        elapsed_time = end_time - start_time
        final_io = current_process.io_counters()
        final_cpu_times = current_process.cpu_times()

        # Get CPU usage based on actual CPU time consumed
        cpu_time_used = (final_cpu_times.user - initial_cpu_times.user + 
                         final_cpu_times.system - initial_cpu_times.system)
        cpu_usage = (cpu_time_used / elapsed_time) * 100 if elapsed_time > 0 else 0

        # Get peak memory usage from signing
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        current_mem_mb = current_mem / (1024 * 1024)
        peak_mem_mb = peak_mem / (1024 * 1024)

        # Get I/O usage - try read_chars first (includes cached I/O)
        try:
            read_bytes = final_io.read_chars - initial_io_info.read_chars
            write_bytes = final_io.write_chars - initial_io_info.write_chars
        except AttributeError:
            # Fallback: actual disk I/O (may be 0 if cached)
            read_bytes = final_io.read_bytes - initial_io_info.read_bytes
            write_bytes = final_io.write_bytes - initial_io_info.write_bytes
            # Alternative: calculate from file sizes
            if read_bytes == 0:
                read_bytes = sum(os.path.getsize(f) for f in files)  # Approximate

        print(f"Execution time: {elapsed_time:.4f} seconds")
        print(f"Maximum additional memory used: {peak_mem_mb - current_mem_mb:.4f} MB")
        print(f"Read: {read_bytes} bytes, Write: {write_bytes} bytes")
        print(f"CPU Usage: {cpu_usage:.2f}%\n")

        # Write to .csv file
        line += f"{end_date_time}"
        line += f"{elapsed_time},"
        line += f"{peak_mem_mb - current_mem_mb},"
        line += f"{cpu_usage},"
        line += f"{read_bytes},"
        line += f"{write_bytes}"
        line += "\n"
        f.write(line)
        tracemalloc.stop()
        
    f.close()