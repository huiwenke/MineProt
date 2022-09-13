# MineProt
<p align="center"><img src="./web/assets/img/logo.png" height="50"/></p>

## Making protein server acessible to all!
MineProt provides solution for curating high-throughput structuring data from AI systems such as [AlphaFold](https://github.com/deepmind/alphafold), [ColabFold](https://github.com/sokrypton/ColabFold), etc. By the aid of MineProt toolkit, you can:
- Deploy your own protein server in simple steps
- Take advantage of most information provided by AI systems to curate your data
- Visualize, browse or search your data via user-friendly online interface
- Utilize plugins to extend the functionality of your server

## Quick start
### Deployment
Linux systems with [docker](https://www.docker.com/) and [docker-compose](https://github.com/docker/compose) are best for MineProt deployment:
```bash
git clone https://github.com/huiwenke/MineProt.git
cd MineProt
toolkit/setup.sh -p 80 -d ./data
```
After a few minutes, you can access your MineProt site at http://localhost.
### Import data
Above all, please get your python3 ready and install dependencies:
```bash
cd toolkit/scripts
pip3 install -r requirements.txt
```
Then, use scripts in MineProt toolkit to import your data. For example, if you employ *colabfold_search* and *colabfold_batch* with parameters `--zip` `--amber` to generate large scale structure predictions, run the command below to import:
```bash
colabfold/import.sh /path/to/your/results --repo new_repo \
--name-mode 1 \
--zip \
--relax \
--python /usr/bin/python3 \
--url http://localhost
```
You will finally find the protein repository *new_repo* at the homepage of your MineProt site, where all proteins have been annotated with UniProt, GO and InterPro, and their structures are visible online. You can easily get their information through the search box in the upper left corner.
## Browser Compatibility
| Chrome | Firefox | Microsoft Edge | Opera | Safari |
| ------ | ------- | -------------- | ----------------- | ------ |
| 67.0+  | 52.9+   | 105.0.1343.27   | 90.0.4480.107      | 13.04  |