#!/bin/bash -ex

# get versionfinder
vfdir=$(mktemp -d -p /tmp test_package_update.XXXX)
git clone git@github.com:jantman/versionfinder.git $vfdir

srcdir=$(mktemp -d -p /tmp test_package_update.XXXX)
git clone git@github.com:jantman/versionfinder-test-pkg.git $srcdir
cd $srcdir
git checkout master
git branch -a | grep -q 'origin/testbranch' && git push origin --delete testbranch
git branch -a | grep -q testbranch && git branch -D testbranch

virtualenv --python=python2.7 .
source bin/activate

# bump version
ver=$(grep '^VERSION' versionfinder_test_pkg/version.py | awk '{print $3}' | sed "s/'//g")
minver=$(echo "$ver" | awk -F . '{print $3}')
verprefix=$(echo "$ver" | awk -F . '{print $1"."$2"."}')
newmin=$(expr $minver + 1)
newver="${verprefix}${newmin}"
sed -i "s/VERSION = '${ver}'/VERSION = '${newver}'/" versionfinder_test_pkg/version.py
git add versionfinder_test_pkg/version.py
git commit -m "bump version from ${ver} to ${newver}"
git push origin

pip install $vfdir
python setup.py develop

# tag
git tag -a $newver -m "${newver} released $(date +%Y-%m-%d)"
tag_commit=$(git rev-parse HEAD)
git push origin $newver

# binaries
python setup.py sdist
python setup.py bdist_wheel

# 2.7 egg
python setup.py bdist_egg
deactivate

# other eggs
#for py in python2.6 python3.3 python3.4 python3.5; do
for py in python2.6; do
    if [[ "$py" == "python3.2" ]]; then
        # we need virtualenv==13.1.2 on py32
        bin/pip install virtualenv==13.1.2
        bin/virtualenv --python=$py venv_$py
    else
        virtualenv --python=$py venv_$py
    fi
    source venv_${py}/bin/activate
    pip install $vfdir
    python setup.py bdist_egg
    deactivate
done

source bin/activate

# new commit
echo "test_package_update.sh at $(date)" >> README.rst
git add README.rst
git commit -m "commit on master"
master_commit=$(git rev-parse HEAD)
git push origin

# branch
git checkout -b testbranch
echo 'testbranch commit' >> README.rst
git add README.rst
git commit -m "testbranch commit"
branch_commit=$(git rev-parse HEAD)
git push origin testbranch

echo "YOU MUST upload the release packages in ${srcdir}/dist"
echo "You must also update acceptance tests with:"
cat <<EOF
TEST_PROJECT = 'versionfinder_test_pkg'
TEST_GIT_HTTPS_URL = 'https://github.com/jantman/versionfinder-test-pkg.git'
TEST_PROJECT_URL = 'https://github.com/jantman/versionfinder-test-pkg'
TEST_VERSION = '${newver}'
TEST_TAG = '${newver}'
TEST_TAG_COMMIT = '${tag_commit}'
TEST_MASTER_COMMIT = '${master_commit}'
TEST_BRANCH = 'testbranch'
TEST_BRANCH_COMMIT = '${branch_commit}'
EOF
