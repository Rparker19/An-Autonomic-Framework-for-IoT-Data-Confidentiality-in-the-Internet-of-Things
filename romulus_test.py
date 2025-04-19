#!/usr/bin/python3

import romulus
import psutil, time
from random import Random

def print_process_info():
    for process in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        print(f"PID: {process.info['pid']}, Name: {process.info['name']}, CPU: {process.info['cpu_percent']}%, Memory: {process.info['memory_info'].rss / (1024 * 1024):.2f} MB")

def run_romulus(data):
    rng = Random()
    
    key = rng.randbytes(16)
    nonce = rng.randbytes(12)
    ad = bytes("romulus-test")
    
    start_time = time.time()
    encrypted, tag = romulus.romulusn_encrypt(key, nonce, ad, data)
    print_process_info()
    total_time = time.time() - start_time
    throughput = data.size() / total_time
    print("Encryption time: %s" % (total_time))
    print("Throughput: %s" % throughput)

    flg, dec = romulus.romulusn_decrypt(key, nonce, tag, ad, encrypted)
    assert flg


if __name__ == "__main__":
    with open("test_file", "rb") as data:
        run_romulus(data)
