#!/bin/bash -e
# --python
# --scripts-dir
# --repo
# --name-mode
# --zip
# --relax
# --url

Python_Path="python3"
MineProt_Scripts_Path="scripts"
MineProt_Repo=""
MineProt_NameMode="0"
MineProt_Zip=""
MineProt_Relax=""
MineProt_URL="http://127.0.0.1"

while [ -n "$1" ]
do
    case "$1" in
        --python)
            Python_Path="$2"
            shift
        ;;
        --scripts-dir)
            MineProt_Scripts_Path=$2
            shift
        ;;
        --repo)
            MineProt_Repo=$2
            shift
        ;;
        --name-mode)
            MineProt_NameMode=$2
            shift
        ;;
        --zip)
            MineProt_Zip="-z"
        ;;
        --relax)
            MineProt_Relax="-r"
        ;;
        --url)
            MineProt_URL=$2
            shift
        ;;
        *)
            InputDir=$1
            UUID=`cat /proc/sys/kernel/random/uuid`
            TmpDir="/tmp/MP-$UUID"
            TmpLog="/tmp/MP-$UUID.log"
        ;;
    esac
    shift
done

echo "Log path: $TmpLog"
echo `date` > $TmpLog

cmd="$Python_Path $MineProt_Scripts_Path/colabfold/transform.py -i $InputDir -o $TmpDir -n $MineProt_NameMode --url $MineProt_URL/api/pdb2alphacif/ $MineProt_Zip $MineProt_Relax >> $TmpLog"
echo "Running colabfold/transform: $cmd"
$cmd

cmd="$Python_Path $MineProt_Scripts_Path/import2es.py -i $TmpDir -n $MineProt_Repo --url $MineProt_URL/api/es -a >> $TmpLog"
echo "Running import2es: $cmd"
$cmd

cmd="$Python_Path $MineProt_Scripts_Path/import2repo.py -i $TmpDir -n $MineProt_Repo --url $MineProt_URL/api/import2repo/ >> $TmpLog"
echo "Running import2repo: $cmd"
$cmd

echo "Done."
echo `date` >> $TmpLog
rm -rf $TmpDir