#!/bin/bash

KCI_DEV="poetry run kci-dev"
GITURL="https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux-stable-rc.git"


declare -a releases=(
    "linux-6.12.y 3f47dc0fd5b11e6655e9fa78a350d64c0a3d53d3"
    "linux-6.6.y ae86bb742fa81e7826a49817e016bf288015f456"
    "linux-6.1.y 9f320894b9c2f9e21bda8aac6c57a2e6395f8eba"
    "linux-5.15.y 4b281055ccfba614e9358cac95fc81a1e79a5d7e"
    "linux-5.10.y 2146a7485c27f6f8373bb5570dee22631a7183a4"
    "linux-5.4.y 3612365cb6b2a875194a5f6d7bc8df7cc26476b3"
)

for release in "${releases[@]}"; do
    read -a strarr <<< "$release"
    BRANCH=${strarr[0]}
    COMMIT=${strarr[1]}
    echo "### $BRANCH - $COMMIT"
    $KCI_DEV results --commit $COMMIT --giturl $GITURL --branch $BRANCH
    echo ""
done
