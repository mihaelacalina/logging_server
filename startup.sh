script_dir=$(dirname $(readlink -f $0))

while true; do
    python "${script_dir}/startup.py"

    sleep 1
done