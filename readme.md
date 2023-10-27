## Cron
Add to `crontab -e` commands below:

- 00 00 * * * cd path_to_dir/ && /usr/bin/python reboot_script.py
- @reboot cd path_to_dir/ && nohup python main.py > output.log 2>&1 &

Make files executable if there's some problems (`main.py` and `reboot_script.py`).

