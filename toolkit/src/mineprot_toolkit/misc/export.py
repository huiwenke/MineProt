import argparse
import base64
import gzip
import json
import os

import requests


def main(argv=None):
    # List arguments
    parser = argparse.ArgumentParser(description="Export data from MineProt Search Page.")
    parser.add_argument("url", type=str, nargs="+", help="Search URL. THIS ARGUMENT IS MANDATORY.")
    parser.add_argument(
        "-o", type=str, default="./MineProt_Search_Results", help="Path to output folder."
    )

    args = parser.parse_args(argv)
    output_dir = args.o
    if not os.path.exists(output_dir):
        print("Output directory " + output_dir + " not exist. Creating ...")
        os.makedirs(output_dir)

    search_url = args.url[0]
    mine_prot_url = search_url.split("/search.php")[0]
    response = requests.get(search_url, timeout=(10, 60))
    response.raise_for_status()
    search_results = json.loads(base64.b64decode(response.text.split("|JSON|")[1]))
    with open(os.path.join(output_dir, "result.json"), "w") as fout_json:
        fout_json.write(json.dumps(search_results))
    for search_result in search_results:
        repo = search_result["_index"]
        repo_path = os.path.join(output_dir, repo)
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
        protein = search_result["_source"]["name"]
        for suffix in [".pdb", ".cif", ".json", ".a3m"]:
            response = requests.get(
                mine_prot_url + "/repo/" + repo + "/" + protein + suffix, timeout=(10, 60)
            )
            if response.status_code == 200:
                with open(os.path.join(repo_path, protein + suffix), "w") as fo:
                    fo.write(response.text)
            response = requests.get(
                mine_prot_url + "/repo/" + repo + "/" + protein + suffix + ".gz", timeout=(10, 60)
            )
            if response.status_code == 200:
                with open(os.path.join(repo_path, protein + suffix), "w") as fo:
                    fo.write(gzip.decompress(response.content).decode())


if __name__ == "__main__":
    raise SystemExit(main())
