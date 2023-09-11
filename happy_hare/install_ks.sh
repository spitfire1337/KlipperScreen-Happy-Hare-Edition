#!/bin/bash
#
# MMU KlipperScreen Happy Hare edition supplemental installer
#
# Copyright (C) 2023  moggieuk#6538 (discord)
#                     moggieuk@hotmail.com
#
# Screen Capture: scrot -s -D :0.0
#
KLIPPER_CONFIG_HOME="${HOME}/printer_data/config"
OLD_KLIPPER_CONFIG_HOME="${HOME}/klipper_config"
PYTHON="python3-virtualenv virtualenv python3-distutils opencv-python"

declare -A PIN 2>/dev/null || {
    echo "Please run this script with ./bash $0"
    exit 1
}

# Screen Colors
OFF='\033[0m'             # Text Reset
BLACK='\033[0;30m'        # Black
RED='\033[0;31m'          # Red
GREEN='\033[0;32m'        # Green
YELLOW='\033[0;33m'       # Yellow
BLUE='\033[0;34m'         # Blue
PURPLE='\033[0;35m'       # Purple
CYAN='\033[0;36m'         # Cyan
WHITE='\033[0;37m'        # White

B_RED='\033[1;31m'        # Bold Red
B_GREEN='\033[1;32m'      # Bold Green
B_YELLOW='\033[1;33m'     # Bold Yellow
B_CYAN='\033[1;36m'       # Bold Cyan

INFO="${CYAN}"
EMPHASIZE="${B_CYAN}"
ERROR="${B_RED}"
WARNING="${B_YELLOW}"
PROMPT="${CYAN}"
INPUT="${OFF}"

function nextsuffix {
    local name="$1"
    local -i num=0
    while [ -e "$name.0$num" ]; do
        num+=1
    done
    printf "%s.0%d" "$name" "$num"
}

verify_not_root() {
    if [ "$EUID" -eq 0 ]; then
        echo -e "${ERROR}This script must not run as root"
        exit -1
    fi
}

check_klipper() {
    if [ "$(sudo systemctl list-units --full -all -t service --no-legend | grep -F "klipper.service")" ]; then
        echo -e "${INFO}Klipper service found"
    else
        echo -e "${ERROR}Klipper service not found! Please install Klipper first"
        exit -1
    fi

}

verify_home_dirs() {
    if [ ! -d "${KLIPPER_CONFIG_HOME}" ]; then
        if [ ! -d "${OLD_KLIPPER_CONFIG_HOME}" ]; then
            echo -e "${ERROR}Klipper config directory (${KLIPPER_CONFIG_HOME} or ${OLD_KLIPPER_CONFIG_HOME}) not found. Use '-c <dir>' option to override"
            exit -1
        fi
        KLIPPER_CONFIG_HOME="${OLD_KLIPPER_CONFIG_HOME}"
    fi
    echo -e "${INFO}Klipper config directory (${KLIPPER_CONFIG_HOME}) found"
}

install_packages()
{
    echo_text "Update package data"
    sudo apt-get update

    echo_text "Checking for broken packages..."
    output=$(dpkg-query -W -f='${db:Status-Abbrev} ${binary:Package}\n' | grep -E ^.[^nci])
    if [ $? -eq 0 ]; then
        echo_text "Detected broken packages. Attempting to fix"
        sudo apt-get -f install
        output=$(dpkg-query -W -f='${db:Status-Abbrev} ${binary:Package}\n' | grep -E ^.[^nci])
        if [ $? -eq 0 ]; then
            echo_error "Unable to fix broken packages. These must be fixed before KlipperScreen can be installed"
            exit 1
        fi
    else
        echo_ok "No broken packages"
    fi

    sudo apt-get install -y $PYTHON
    if [ $? -eq 0 ]; then
        echo_ok "Installed Python dependencies"
    else
        echo_error "Installation of Python dependencies failed ($PYTHON)"
        exit 1
    fi

#     ModemManager interferes with klipper comms
#     on buster it's installed as a dependency of mpv
#     it doesn't happen on bullseye
    sudo systemctl mask ModemManager.service
}


install_klipper_screen() {
    echo -e "${INFO}Adding KlipperScreen support for MMU"
    do_install=0
    ks_config="${KLIPPER_CONFIG_HOME}/KlipperScreen.conf"
    hh_config="${KLIPPER_CONFIG_HOME}/mmu_klipperscreen.conf"

    # Backup old Klippersreen Happy Hare menus
    if [ -f "${hh_config}" ]; then
        next_hh_config="$(nextsuffix "$hh_config")"
        echo -e "${WARNING}Pre upgrade config file moved to ${next_hh_config} for reference"
        mv ${hh_config} ${next_hh_config}
    fi

    # Ensure KlipperScreen.conf includes Happy Hare menus
    cat << EOF > /tmp/KlipperScreen.conf.tmp
# 
# MMU "Happy Hare edition" menus
#
[include mmu_klipperscreen.conf]

EOF

    if [ -f "${ks_config}" ]; then
        update_section=$(grep -c '\[include mmu_klipperscreen.conf\]' ${ks_config} || true)
        if [ "${update_section}" -eq 0 ]; then
            cat ${ks_config} >> /tmp/KlipperScreen.conf.tmp && cp /tmp/KlipperScreen.conf.tmp ${ks_config}
        else
            echo -e "${INFO}KlipperScreen MMU include already exists in conf. Skipping install"
        fi
    else
        cp /tmp/KlipperScreen.conf.tmp ${ks_config}
    fi

    echo -e "${INFO}Installing Happy Hare menus..."
    max_gate=$(expr $num_gates - 1)
    cp ${SRCDIR}/menus.conf "${hh_config}"

    for file in `ls ${SRCDIR}/iter*.conf`; do
        token=`basename $file .conf`
        echo -e "    ${INFO}Expanding menu ${token} for ${num_gates} gates"
	expanded=$(for i in $(eval echo "{0..`expr $num_gates - 1`}"); do
            cat ${SRCDIR}/${token}.conf | sed -e "s/{i}/${i}/g"
        done)
        expanded="# Generated menus for each tool/gate...\n${expanded}"
        awk -v r="$expanded" "{gsub(/^MMU_${token}/,r)}1" "${hh_config}" > /tmp/mmu_klipperscreen.conf.tmp && mv /tmp/mmu_klipperscreen.conf.tmp "${hh_config}"
    done

    # Always ensure images are linked for every style
    for style in `ls -d ${HOME}/KlipperScreen/styles/*/images`; do
        for img in `ls ${SRCDIR}/images`; do
            ln -sf "${SRCDIR}/images/${img}" "${style}/${img}"
        done
    done

    restart_klipperscreen
}

install_update_manager() {
    echo -e "${INFO}Adding update manager to moonraker.conf"
    echo "${KLIPPER_CONFIG_HOME}/moonraker.conf"
    if [ -f "${KLIPPER_CONFIG_HOME}/moonraker.conf" ]; then
        orig_section=$(grep -c '\[update_manager KlipperScreen\]' \
            ${KLIPPER_CONFIG_HOME}/moonraker.conf || true)
        if [ "${orig_section}" -ne 0 ]; then
            echo -e "${WARNING}Original [update_manager KlipperScreen] commented out in moonraker.conf"
            cat ${KLIPPER_CONFIG_HOME}/moonraker.conf | sed -e " \
                /^\[update_manager KlipperScreen\]/,+7 s/^/#/; \
                    " > /tmp/moonraker.conf.tmp && mv /tmp/moonraker.conf.tmp ${KLIPPER_CONFIG_HOME}/moonraker.conf
        fi
        update_section=$(grep -c '\[update_manager KlipperScreen-happy_hare\]' \
            ${KLIPPER_CONFIG_HOME}/moonraker.conf || true)
        if [ "${update_section}" -eq 0 ]; then
            echo "" >> ${KLIPPER_CONFIG_HOME}/moonraker.conf
            while read -r line; do
                echo -e "${line}" >> ${KLIPPER_CONFIG_HOME}/moonraker.conf
            done < "${SRCDIR}/moonraker_update.txt"
            echo "" >> ${KLIPPER_CONFIG_HOME}/moonraker.conf
            restart_moonraker
        else
            echo -e "${WARNING}[update_manager KlipperScreen-happy_hare] already exist in moonraker.conf - skipping install"
        fi
    else
        echo -e "${WARNING}Moonraker.conf not found!"
    fi
}

restart_klipperscreen() {
    echo -e "${INFO}Restarting KlipperScreen..."
    sudo systemctl restart KlipperScreen
}

restart_moonraker() {
    echo -e "${INFO}Restarting Moonraker..."
    sudo systemctl restart moonraker
}

# Force script to exit if an error occurs
set -e
clear

# Find SRCDIR from the pathname of this script
SRCDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/ && pwd )"

while getopts "c:g:" arg; do
    case $arg in
        c) KLIPPER_CONFIG_HOME=${OPTARG};;
        g) num_gates=$OPTARG;;
    esac
done
if [ -z "$num_gates" ]; then
    echo "Must specify the number of gates (selectors) with the -g <num_gates> argument" >&2
    exit 1
fi

verify_not_root
verify_home_dirs
install_packages
install_klipper_screen
install_update_manager

echo -e "${EMPHASIZE}"
echo "Done.  Enjoy KlipperScreen Happy Hare Edition!"
echo -e "${INFO}"
echo '(\_/)'
echo '( *,*)'
echo '(")_(") MMU Ready'
echo

