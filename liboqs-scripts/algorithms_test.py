import logging
from pprint import pformat
from sys import stdout

import oqs
import time
import tracemalloc

files = ["A Brief Introduction to Neural Networks (neuronalenetze-en-zeta2-2col-dkrieselcom).pdf"]

def signing(alg):
    with oqs.Signature(alg) as signer, oqs.Signature(alg) as verifier:
        # Signer generates its keypair
        signer_public_key = signer.generate_keypair()

        for filename in files:
            with open(filename, 'rb') as file:
                pdf_bytes = file.read()

                # Signer signs the message
                signature = signer.sign(pdf_bytes)

                # Verifier verifies the signature
                is_valid = verifier.verify(pdf_bytes, signature, signer_public_key)
                print(f"Valid signature? {is_valid}\t|\t")

# Create signer and verifier with sample signature mechanisms
sigalgs = ["Falcon-512", "Falcon-1024", "ML-DSA-44", "ML-DSA-65", "ML-DSA-87", "SPHINCS+-SHA2-128f-simple", "SPHINCS+-SHA2-192f-simple", "SPHINCS+-SHA2-256f-simple"]
for alg in sigalgs:
    print(f"Algorithm: {alg}\t|\t")
    start_time = time.perf_counter()
    tracemalloc.start()

    signing(alg)

    end_time = time.perf_counter()
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    current_mem_mb = current_mem / (1024 * 1024)
    peak_mem_mb = peak_mem / (1024 * 1024)

    elapsed_time = end_time - start_time
    print(f"Execution time: {elapsed_time:.4f} seconds")
    print(f"Maximum additional memory used: {peak_mem_mb - current_mem_mb:.4f} MB\n")
    tracemalloc.stop()