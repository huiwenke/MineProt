#!/bin/bash -e

OutputPath=./output.3di

while [ -n "$1" ]
do
    case "$1" in
        --help)
            echo "Usage: fsdb2seq.sh /path/to/fsdb path/to/3di_fasta"
            exit
        ;;
        *)
            InputPath=$1
            OutputPath=$2
            shift
        ;;
    esac
    shift
done

if [ -z $InputPath ]; then
    echo "Error: Invalid inputs."
    $0 --help
    exit
fi

Input_h=$InputPath"_h"
Input_ss=$InputPath"_ss"
paste $Input_h $Input_ss | tr -cd "[:print:]\n\t" | sed "s/^/>/" | sed "s/\t/\n/" > $OutputPath