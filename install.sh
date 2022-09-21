#!/usr/bin/env bash

usage()
{
  echo "Usage: install.sh [ -u  Update]
                  [ -t  Run tests ]
                  [ -p  Set Python version]
            "
  exit 2
}

unamestr=`uname`
if [ "$unamestr" == 'Linux' ]; then
    prof=~/.bashrc
    mini_conda_url=https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
    matplotlibdir=~/.config/matplotlib
    output_txt_file=deployment_linux.txt
elif [ "$unamestr" == 'FreeBSD' ] || [ "$unamestr" == 'Darwin' ]; then
    prof=~/.bash_profile
    mini_conda_url=https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
    matplotlibdir=~/.matplotlib
    output_txt_file=deployment_macos.txt
else
    echo "Unsupported environment. Exiting."
    exit
fi

source $prof
DEFAULT_PYVER=3.9
PYVER=$DEFAULT_PYVER
create_deploy_yaml=false
run_tests=false
input_txt_file=$output_txt_file
input_yaml_file=""
while getopts ":utp:" options; do
    case "${options}" in                    # 
    u)                                    # If the option is u,
        input_yaml_file=source_environment.yml
        create_deploy_yaml=true
        run_tests=true
        ;;
    t)
        run_tests=true
        ;;
    p)
        PYVER=${OPTARG}
        ;;
    *)                                    # If unknown (any other) option:
      usage                       # Exit abnormally.
      ;;
    esac
done

# make sure -p is only checked if -u is also
if [[ "${PYVER}" != "${DEFAULT_PYVER}" && $create_deploy_yaml != "true" ]]; then
    echo "Error: -p option can only be used with -u option. Exiting."
    exit 1
fi

echo "YAML file to use as input: ${input_yaml_file}"
echo "Variable to indicate deployment: ${create_deploy_yaml}"


# name of conda forge C compiler
CC_PKG=c-compiler

# Name of virtual environment
VENV=shakemap



# Start in conda base environment
echo "Activate base virtual environment"
# eval "$(conda shell.bash hook)"                                                
conda activate base

# Remove existing shakemap environment if it exists
conda remove -y -n $VENV --all
conda clean -y --all

# install mamba as it makes solving MUCH faster
which mamba
if [ $? -eq 0 ]; then
   echo OK
else
    echo "Installing mamba in base environment..."
    conda install mamba -n base -c conda-forge --strict-channel-priority -y
fi

# Install the virtual environment
echo "Creating the $VENV virtual environment:"
if [ -z "${input_yaml_file}" ]; then
    echo "Creating environment from spec list: ${input_txt_file}"
    mamba create --name $VENV --file "${input_txt_file}"
else
    echo "Creating new environment from environment file: ${input_yaml_file} with python version ${PYVER}"
    # change python version in yaml file to match PYVER

    sed 's/python=3.9/python='"${PYVER}"'/' "${input_yaml_file}" > tmp.yml
    mamba env create -f tmp.yml
    rm tmp.yml 
fi


# Bail out at this point if the conda create command fails.
# Clean up zip files we've downloaded
if [ $? -ne 0 ]; then
    echo "Failed to create conda environment.  Resolve any conflicts, then try again."
    exit 1
fi

# Activate the new environment
echo "Activating the $VENV virtual environment"
conda activate $VENV

# if conda activate fails, bow out gracefully
if [ $? -ne 0 ];then
    echo "Failed to activate ${VENV} conda environment. Exiting."
    exit 1
fi

# The presence of a __pycache__ folder in bin/ can cause the pip
# install to fail... just to be safe, we'll delete it here.
if [ -d bin/__pycache__ ]; then
    rm -rf bin/__pycache__
fi

echo "#############Installing pip dependencies##############"
pip install --no-dependencies -r requirements.txt 
# pip install --upgrade --no-dependencies https://github.com/gem/oq-engine/archive/engine-3.12.zip

# Touch the C code to make sure it gets re-compiled
echo "Installing ${VENV}..."
touch shakemap/c/*.pyx
touch shakemap/c/contour.c

# Install this package
echo "#############Installing shakemap code##############"
pip install --no-deps -e .

# now if the user has explicitly asked to run tests OR they're doing an update
if  $run_test; then
    echo "Running tests..."
    py.test --cov=.
    if [ $? -eq 0 ]; then
        if [ "${create_deploy_yaml}" == "true" ]; then
            conda list --explicit  > "${output_txt_file}"
            echo "Updated dependency file for your platform: ${output_txt_file}."
        fi
    else
        echo "Tests failed. Please resolve these issues then trying re-installing."
    fi
fi
