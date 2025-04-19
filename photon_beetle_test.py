#!/usr/bin/python3

import photon_beetle
import psutil, time
from random import Random

def print_process_info():
    for process in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        print(f"PID: {process.info['pid']}, Name: {process.info['name']}, CPU: {process.info['cpu_percent']}%, Memory: {process.info['memory_info'].rss / (1024 * 1024):.2f} MB")

def run_photon_beetle(data):
    rng = Random()
    
    key = rng.randbytes(16)
    nonce = rng.randbytes(12)
    ad = bytes("photon-beetle-test")
    
    start_time = time.time()
    encrypted, tag = photon_beetle.photon_beetle_128_encrypt(key, nonce, ad, data)
    print_process_info()
    total_time = time.time() - start_time
    throughput = data.size() / total_time
    print("Encryption time: %s" % (total_time))
    print("Throughput: %s" % throughput)

    flg, dec = photon_beetle.photon_beetle_128_decrypt(key, nonce, tag, ad, encrypted)
    assert flg


if __name__ == "__main__":
    with open("test_file", "rb") as data:
        run_photon_beetle(data)
