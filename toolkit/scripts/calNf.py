import argparse
import os
import tempfile
import gzip
import lzma
import bz2
import subprocess
import concurrent.futures

def a3m_to_aln(a3m_text):
    aln_lines = []
    for line in a3m_text.splitlines():
        if line.startswith('#') or line.startswith('>'):
            continue
        aln_lines.append(''.join([c for c in line if not c.islower()]))
    return '\n'.join(aln_lines)

def decompress_and_convert(a3m_path, aln_dir):
    filename = os.path.basename(a3m_path)
    if filename.endswith(('.gz', '.xz', '.bz2')):
        if filename.endswith('.gz'):
            open_func = gzip.open
        elif filename.endswith('.xz'):
            open_func = lzma.open
        elif filename.endswith('.bz2'):
            open_func = bz2.open
        with open_func(a3m_path, 'rt') as f:
            a3m_text = f.read()
    else:
        with open(a3m_path, 'r') as f:
            a3m_text = f.read()
    
    aln_text = a3m_to_aln(a3m_text)
    aln_path = os.path.join(aln_dir, os.path.splitext(filename)[0] + ".aln")
    with open(aln_path, 'w') as f:
        f.write(aln_text)
    return aln_path

def run_calNf(aln_path, calNf_exec, s, norm, max_val, nonre):
    cmd = [calNf_exec, aln_path, str(s), str(norm), str(max_val)]
    if nonre is not None:
        cmd.append(str(nonre))
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--a3m", required=True)
    parser.add_argument("--calNf", default="calNf")
    parser.add_argument("-t", type=int, default=1)
    parser.add_argument("-s", type=float, default=0.8)
    parser.add_argument("--norm", type=int, default=0)
    parser.add_argument("--max", type=int, default=0)
    parser.add_argument("--nonre", type=int, default=None)
    
    args = parser.parse_args()
    
    with tempfile.TemporaryDirectory() as aln_dir:
        a3m_files = [os.path.join(args.a3m, f) for f in os.listdir(args.a3m) 
                    if os.path.isfile(os.path.join(args.a3m, f)) and f.endswith(('.a3m', '.gz', '.xz', '.bz2'))]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.t) as executor:
            aln_paths = list(executor.map(lambda f: decompress_and_convert(f, aln_dir), a3m_files))
        
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.t) as executor:
            future_to_file = {executor.submit(run_calNf, aln, args.calNf, args.s, args.norm, args.max, args.nonre): os.path.basename(aln) 
                            for aln in aln_paths}
            for future in concurrent.futures.as_completed(future_to_file):
                filename = os.path.splitext(future_to_file[future])[0]
                try:
                    results[filename] = future.result()
                except Exception as e:
                    results[filename] = f"Error: {str(e)}"
        
        for key, value in results.items():
            print(f"{key}\t{value}")

if __name__ == "__main__":
    main()