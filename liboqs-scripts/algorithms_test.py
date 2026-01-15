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
import numpy as np
import platform

# Parameters
should_create_random_files = False
number_of_files = 5
min_file_size_in_mb = 10  # Starting size (will double for each file)
file_extension = "bin"


def get_temperature():
    """Get CPU temperature if available"""
    try:
        temps = psutil.sensors_temperatures()
        if 'cpu_thermal' in temps:
            return temps['cpu_thermal'][0].current
        elif 'coretemp' in temps:
            return temps['coretemp'][0].current
    except:
        pass
    return None


def get_rpi_model():
    """Get Raspberry Pi model"""
    try:
        result = subprocess.check_output(['cat', '/proc/device-tree/model']).decode().strip()
        return f"rpi_{result.split()[2]}"  # Return model number
    except:
        return "Unknown"


def get_device_info():
    """Get device hardware information"""
    return {
        'cpu_count': psutil.cpu_count(logical=False),
        'cpu_count_logical': psutil.cpu_count(logical=True),
        'cpu_freq_max': psutil.cpu_freq().max if psutil.cpu_freq() else 0,
        'cpu_freq_current': psutil.cpu_freq().current if psutil.cpu_freq() else 0,
        'total_ram_mb': psutil.virtual_memory().total / (1024 * 1024),
        'available_ram_mb': psutil.virtual_memory().available / (1024 * 1024),
        'architecture': platform.machine(),
        'device_model': get_rpi_model()
    }


def get_system_state():
    """Get current system load and state"""
    return {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_io_read_mb': psutil.disk_io_counters().read_bytes / (1024 * 1024),
        'disk_io_write_mb': psutil.disk_io_counters().write_bytes / (1024 * 1024),
        'process_count': len(psutil.pids()),
        'load_average': os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
    }


def create_random_files(filename, num_files, min_size_in_mb=10, extension="bin"):
    """Create random files with exponentially increasing sizes"""
    for i in range(num_files):
        # Calculate size: min_size * 2^i (doubles each time)
        current_size_mb = min_size_in_mb * (2 ** i)
        
        filepath = Path(__file__).parent / f'{Path(filename).stem}_{i}.{extension}'
        print(f"Creating file {i+1}/{num_files}: {filepath.name} ({current_size_mb} MB)")
        
        with open(filepath, "wb") as f:
            f.write(os.urandom(current_size_mb * 1024 * 1024))
    
    print(f"Created {num_files} files with sizes from {min_size_in_mb} MB to {min_size_in_mb * (2 ** (num_files-1))} MB")


def get_data_characteristics(files):
    """Analyze input data characteristics"""
    total_size = sum(os.path.getsize(f) for f in files)
    file_sizes = [os.path.getsize(f) for f in files]
    
    return {
        'num_files': len(files),
        'total_size_mb': total_size / (1024 * 1024),
        'avg_file_size_mb': (total_size / len(files)) / (1024 * 1024),
        'min_file_size_mb': min(file_sizes) / (1024 * 1024),
        'max_file_size_mb': max(file_sizes) / (1024 * 1024),
        'file_size_variance': np.var(file_sizes) / (1024 * 1024)
    }


def get_algorithm_features(alg):
    """Get algorithm-specific static features"""
    with oqs.Signature(alg) as sig:
        return {
            'public_key_size': len(sig.generate_keypair()),
            'signature_length': sig.signature_length,
            'algorithm_name': alg,
            'algorithm_family': alg.split('-')[0]  # e.g., 'Falcon', 'ML-DSA'
        }

def signing(alg, files):
    # Create signer and verifier
    with oqs.Signature(alg) as signer, oqs.Signature(alg) as verifier:
        # Signer generates its keypair
        signer_public_key = signer.generate_keypair()

        total_signature_size = 0

        # Sign each file in the list
        for filename in files:
            with open(filename, 'rb') as file:
                bytes = file.read()

                # Signer signs the message
                signature = signer.sign(bytes)

                # Keep track of total signature size
                total_signature_size += len(signature)

                # Verifier verifies the signature
                is_valid = verifier.verify(bytes, signature, signer_public_key)
                print(f"Valid signature ({Path(filename).name})? {is_valid}\t|\t")
        print(f"Total signature size for algorithm {alg}: {total_signature_size} bytes")
        return total_signature_size
    

def signing_with_detailed_metrics(alg, files):
    """Enhanced signing with per-file metrics"""
    with oqs.Signature(alg) as signer, oqs.Signature(alg) as verifier:
        signer_public_key = signer.generate_keypair()
        
        total_signature_size = 0
        per_file_times = []
        per_file_signature_sizes = []
        
        for filename in files:
            file_start = time.perf_counter()
            
            with open(filename, 'rb') as file:
                bytes_data = file.read()
                signature = signer.sign(bytes_data)
                total_signature_size += len(signature)
                per_file_signature_sizes.append(len(signature))
                is_valid = verifier.verify(bytes_data, signature, signer_public_key)
                print(f"Valid signature ({Path(filename).name})? {is_valid}\t|\t")
            
            file_elapsed = time.perf_counter() - file_start
            per_file_times.append(file_elapsed)
        
        return {
            'total_signature_size': total_signature_size,
            'avg_time_per_file': np.mean(per_file_times),
            'std_time_per_file': np.std(per_file_times),
            'avg_signature_size': np.mean(per_file_signature_sizes),
            'throughput_mb_per_sec': sum(os.path.getsize(f) for f in files) / (1024 * 1024) / sum(per_file_times)
        }

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
    #f.write("Algorithm,Start Time,End Time,Execution Time (s),Memory Used (MB),CPU Usage (%),Read Bytes,Write Bytes,Total Signature Size (bytes)\n")
    f.write("Algorithm,Start Time,End Time,Execution Time (s),Memory Used (MB),CPU Usage (%),"
            "Read Bytes,Write Bytes,Total Signature Size (bytes),"
            "Num Files,Total Size MB,Avg File Size MB,"
            "CPU Count,Total RAM MB,Available RAM MB,System CPU %,System Memory %,"
            "Avg Time Per File,Throughput MB/s,Temperature C\n")
    
    # Get device info once
    device_info = get_device_info()

    if should_create_random_files:
        # Create random files for testing
        create_random_files("testfile", number_of_files, min_file_size_in_mb, file_extension)

    # Grab all files with the above extension type from the directory
    files = glob.glob(f"{Path(__file__).parent}/*.{file_extension}")

    if len(files) == 0:
        print(f"No files with .{file_extension} extension found in the specified directory. Creating the test files...")
        # Create random files for testing
        create_random_files("testfile", number_of_files, min_file_size_in_mb, file_extension)
        files = glob.glob(f"{Path(__file__).parent}/*.{file_extension}")

    # Get process id
    current_process = psutil.Process(os.getpid())
    #_ = current_process.cpu_percent()

    for idx, alg in enumerate(sigalgs):
        print(f"Algorithm ({idx}/{len(sigalgs)}): {alg}\t|\t")
        line = f"{alg},"

        # Get system state before running
        system_state_before = get_system_state()
        data_chars = get_data_characteristics(files)
        temp_before = get_temperature()

        # Start timer, memory tracing, and i/o tracking
        start_time = time.perf_counter()
        start_date_time = datetime.datetime.now()
        line += f"{start_date_time},"
        tracemalloc.start()
        initial_io_info = current_process.io_counters()
        initial_cpu_times = current_process.cpu_times()

        # Perform signing
        #signature_size = signing(alg, files)
        detailed_metrics = signing_with_detailed_metrics(alg, files)

        # End timer
        end_time = time.perf_counter()
        end_date_time = datetime.datetime.now()
        elapsed_time = end_time - start_time
        final_io = current_process.io_counters()
        final_cpu_times = current_process.cpu_times()

        # Get temperature after signing
        temp_after = get_temperature()
        temp_change = (temp_after - temp_before) if (temp_before and temp_after) else 0

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
            print(f"using read_chars and write_chars for I/O measurement")
        except AttributeError:
            # Fallback: actual disk I/O (may be 0 if cached)
            read_bytes = final_io.read_bytes - initial_io_info.read_bytes
            write_bytes = final_io.write_bytes - initial_io_info.write_bytes
            print(f"using read_bytes and write_bytes for I/O measurement")
            # Alternative: calculate from file sizes
            if read_bytes == 0:
                print("read_bytes was 0, calculating read_bytes from file sizes...")
                read_bytes = sum(os.path.getsize(f) for f in files)  # Approximate

        print(f"Execution time: {elapsed_time:.4f} seconds")
        print(f"Maximum additional memory used: {peak_mem_mb - current_mem_mb:.4f} MB")
        print(f"Read: {read_bytes} bytes, Write: {write_bytes} bytes")
        print(f"CPU Usage: {cpu_usage:.3f}%\n")

        # Write to .csv file
        line += f"{end_date_time},"
        line += f"{elapsed_time},"
        line += f"{peak_mem_mb - current_mem_mb},"
        line += f"{cpu_usage},"
        line += f"{read_bytes},"
        line += f"{write_bytes},"
        line += f"{detailed_metrics['total_signature_size']},"
        line += f"{data_chars['num_files']},"
        line += f"{data_chars['total_size_mb']},"
        line += f"{data_chars['avg_file_size_mb']},"
        line += f"{device_info['cpu_count']},"
        line += f"{device_info['total_ram_mb']},"
        line += f"{device_info['available_ram_mb']},"
        line += f"{system_state_before['cpu_percent']},"
        line += f"{system_state_before['memory_percent']},"
        line += f"{detailed_metrics['avg_time_per_file']},"
        line += f"{detailed_metrics['throughput_mb_per_sec']},"
        line += f"{temp_after if temp_after else 'N/A'}"
        line += "\n"
        f.write(line)
        tracemalloc.stop()
        
    f.close()