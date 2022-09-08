#!/bin/bash -e

Python_Path="/usr/bin/python3"
MineProt_Scripts_Path="."
MineProt_Repo=""
MineProt_NameMode="0"
MineProt_Zip=""
MineProt_Relax=""
MineProt_URL="http://127.0.0.1"

while [ -n "$1" ]
do
    case "$1" in
        --repo)
            MineProt_Repo=$2
            shift
        ;;
        --python)
            Python_Path="$2"
            shift
        ;;
        --scripts-dir)
            MineProt_Scripts_Path=$2
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
        --help)
            echo "Usage: colabfold/import.sh [options...] <data_dir>"
            echo "--repo <name>            MineProt repository name (THIS ARGUMENT IS MANDATORY)"
            echo "--python <dir>           Path to python3 (default: /usr/bin/python3)"
            echo "--scripts-dir <dir>      Path to MineProt scripts (default: .)"
            echo "--name-mode <0|1|2|3>    Naming mode: 0(default): Use prefix; 1: Use name in .a3m; 2: Auto rename; 3: Customize name"
            echo "--zip                    Unzip results"
            echo "--relax                  Use relaxed results"
            echo "--url <url>              MineProt URL (default: http://127.0.0.1)"
            exit
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

if [ ! -d $InputDir ]; then
    echo "Error: Invalid inputs."
    $0 --help
    exit
fi

echo "Log path: $TmpLog"
echo `date` > $TmpLog

cmd="$Python_Path $MineProt_Scripts_Path/colabfold/transform.py -i $InputDir -o $TmpDir -n $MineProt_NameMode --url $MineProt_URL/api/pdb2alphacif/ $MineProt_Zip $MineProt_Relax"
echo "Running colabfold/transform: $cmd"
$cmd >> $TmpLog

cmd="$Python_Path $MineProt_Scripts_Path/import2es.py -i $TmpDir -n $MineProt_Repo --url $MineProt_URL/api/es -a"
echo "Running import2es: $cmd"
$cmd >> $TmpLog

cmd="$Python_Path $MineProt_Scripts_Path/import2repo.py -i $TmpDir -n $MineProt_Repo --url $MineProt_URL/api/import2repo/"
echo "Running import2repo: $cmd"
$cmd >> $TmpLog

echo "Done."
echo `date` >> $TmpLog
rm -rf $TmpDir