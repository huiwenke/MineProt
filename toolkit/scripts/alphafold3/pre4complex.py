import argparse
import os
import json
import random
import gzip
import lzma
import bz2
import threading

def read_fasta(fasta_file):
    sequences = {}
    if not fasta_file or not os.path.exists(fasta_file):
        return sequences
    
    with open(fasta_file, 'r') as f:
        seq_id = None
        seq = []
        for line in f:
            line = line.strip()
            if line.startswith('>'):
                if seq_id:
                    sequences[seq_id] = ''.join(seq)
                seq_id = line[1:].split()[0]
                seq = []
            else:
                seq.append(line)
        if seq_id:
            sequences[seq_id] = ''.join(seq)
    return sequences

def read_a3m_sequence(a3m_file):
    open_func = open
    if a3m_file.endswith('.gz'):
        open_func = gzip.open
    elif a3m_file.endswith('.xz'):
        open_func = lzma.open
    elif a3m_file.endswith('.bz2'):
        open_func = bz2.open
    
    with open_func(a3m_file, 'rt') as f:
        for line in f:
            if line.startswith('#') or line.startswith('>'):
                continue
            return line.strip()
    return ""

def parse_list_file(list_file):
    with open(list_file, 'r') as f:
        return [line.strip().split() for line in f]

def generate_json(proteins, fasta_sequences, a3m_dir, output_dir, num_seeds):
    name = "_x_".join(proteins)
    json_data = {
        "name": name,
        "sequences": [],
        "modelSeeds": [random.randint(0, 2**32 - 1) for _ in range(num_seeds)],
        "dialect": "alphafold3",
        "version": 2
    }
    
    for i, protein in enumerate(proteins):
        sequence = ""
        a3m_path = ""
        
        if a3m_dir:
            for ext in [".a3m", ".a3m.gz", ".a3m.xz", ".a3m.bz2"]:
                potential_path = os.path.join(a3m_dir, protein + ext)
                if os.path.exists(potential_path):
                    sequence = read_a3m_sequence(potential_path)
                    a3m_path = potential_path
                    break
        
        if not sequence and fasta_sequences:
            sequence = fasta_sequences.get(protein, "")
        
        protein_entry = {
            "id": chr(65 + i),
            "sequence": sequence
        }
        
        if a3m_path:
            protein_entry.update({
                "unpairedMsaPath": a3m_path,
                "pairedMsa": "",
                "templates": []
            })
        
        json_data["sequences"].append({"protein": protein_entry})
    
    output_path = os.path.join(output_dir, f"{name}.json")
    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=4)

def worker(protein_groups, fasta_sequences, a3m_dir, output_dir, num_seeds):
    for proteins in protein_groups:
        generate_json(proteins, fasta_sequences, a3m_dir, output_dir, num_seeds)

def main():
    parser = argparse.ArgumentParser(description="Generate JSON files for protein interactions.")
    parser.add_argument("--list", required=True, help="Path to the interaction protein list file")
    parser.add_argument("--fasta", help="Path to the FASTA file")
    parser.add_argument("--a3m", help="Path to the A3M directory")
    parser.add_argument("-o", required=True, help="Output directory")
    parser.add_argument("-t", type=int, default=1, help="Number of threads (default: 1)")
    parser.add_argument("-n", type=int, default=1, help="Number of random seeds (default: 1)")
    
    args = parser.parse_args()
    os.makedirs(args.o, exist_ok=True)
    fasta_sequences = read_fasta(args.fasta) if args.fasta else {}
    protein_groups = parse_list_file(args.list)
    
    num_threads = min(args.t, len(protein_groups))
    threads = []
    chunk_size = (len(protein_groups) + num_threads - 1) // num_threads
    
    for i in range(num_threads):
        chunk = protein_groups[i * chunk_size:(i + 1) * chunk_size]
        thread = threading.Thread(target=worker, args=(chunk, fasta_sequences, args.a3m, args.o, args.n))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()