#!/usr/bin/env python3
import glob
import oqs
import os
import psutil
import sys
import time
import tracemalloc

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
                print(f"Valid signature? {is_valid}\t|\t")

if __name__ == "__main__":
    # List of digital signing algorithms to be tested in this script
    sigalgs = ["Falcon-512", "Falcon-1024", "ML-DSA-44", "ML-DSA-65", "ML-DSA-87", "SPHINCS+-SHA2-128f-simple", "SPHINCS+-SHA2-192f-simple", "SPHINCS+-SHA2-256f-simple",
               "SLH_DSA_PURE_SHA2_128F", "SLH_DSA_PURE_SHA2_192F", "SLH_DSA_PURE_SHA2_256F", "SLH_DSA_PURE_SHAKE_128F", "SLH_DSA_PURE_SHAKE_192F", "SLH_DSA_PURE_SHAKE_256F",
               "cross-rsdp-128-balanced", "cross-rsdp-128-fast", "cross-rsdp-128-small", "cross-rsdp-192-balanced", "cross-rsdp-192-balanced", "cross-rsdp-192-small",
               "cross-rsdp-256-balanced", "cross-rsdp-256-fast", "cross-rsdp-256-small", "MAYO-1", "MAYO-2", "MAYO-3", "MAYO-5", "SNOVA_24_5_4", "SNOVA_56_25_2", "SNOVA_60_10_4",
               "OV-Is", "OV-III", "OV-V"]

    # Output .csv file
    f = open('output.csv', 'w')

    # File extension type to sign in the directory
    file_extension = "pdf"

    # Grab all files with the above extension type from the directory passed as a cmd line arg
    files = glob.glob(f"{sys.argv[1]}/*.{file_extension}")

    # Get process id
    current_process = psutil.Process(os.getpid())
    _ = current_process.cpu_percent()

    for alg in sigalgs:
        print(f"Algorithm: {alg}\t|\t")
        line = f"{alg},"

        # Start timer, memory tracing, and i/o tracking
        start_time = time.perf_counter()
        tracemalloc.start()
        initial_io_info = current_process.io_counters()

        signing(alg, files)

        # End timer
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        final_io = current_process.io_counters()

        # Get CPU usage for the elapsed time to sign the files
        cpu_usage = current_process.cpu_percent(interval=int(elapsed_time)) / psutil.cpu_count()

        # Get peak memory usage from signing
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        current_mem_mb = current_mem / (1024 * 1024)
        peak_mem_mb = peak_mem / (1024 * 1024)

        # Get I/O usage
        read_bytes = final_io.read_bytes - initial_io_info.read_bytes
        write_bytes = final_io.write_bytes - initial_io_info.write_bytes

        print(f"Execution time: {elapsed_time:.4f} seconds")
        print(f"Maximum additional memory used: {peak_mem_mb - current_mem_mb:.4f} MB\n")

        # Write to .csv file
        line += f"{elapsed_time},"
        line += f"{peak_mem_mb - current_mem_mb},"
        line += f"{cpu_usage},"
        line += f"{read_bytes}"
        line += f"{write_bytes}"
        line += "\n"
        f.write(line)
        tracemalloc.stop()
        
    f.close()