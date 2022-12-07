#!/bin/bash -e

OutputDir=./
MineProt_Repo=''

while [ -n "$1" ]
do
    case "$1" in
        --help)
            echo "Usage: msa2seq.sh --repo <repo_name> /path/to/repo_dir path/to/fasta_dir"
            exit
        ;;
        --repo)
            MineProt_Repo=$2
            shift
        ;;
        *)
            InputDir=$1
            OutputDir=$2
            shift
        ;;
    esac
    shift
done

if [ ! -d $InputDir ]; then
    echo "Error: Invalid inputs."
    $0 --help
    exit
fi

if [ -z $MineProt_Repo ]; then
    MineProt_Repo=`basename $InputDir`
fi

OutputPath=$OutputDir/$MineProt_Repo.fasta
echo -n '' > $OutputPath
ls $InputDir | grep ".a3m" | while read msa
do
    MsaPath=$InputDir/$msa
    Seq=`head -3 $MsaPath | tail -1`
    Id=">"`echo $msa | sed "s/.a3m/|repo=${MineProt_Repo}/"`
    echo $Id >> $OutputPath
    echo $Seq >> $OutputPath
done