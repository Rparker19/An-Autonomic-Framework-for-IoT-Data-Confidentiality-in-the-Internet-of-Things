# An-Autonomic-Framework-for-IoT-Data-Confidentiality-in-the-Internet-of-Things
Datasets, data generation script, and ML models for "An Autonomic Framework for IoT Data Confidentiality in the Internet of Things"


# To Install Open-Quantum-Safe library
- Refer to https://github.com/open-quantum-safe/liboqs for more details
- $ pip install liboqs-python
- $ sudo apt install astyle cmake gcc ninja-build libssl-dev python3-pytest python3-pytest-xdist unzip xsltproc doxygen graphviz python3-yaml valgrind
- $ git clone -b main https://github.com/open-quantum-safe/liboqs.git
- $ cd liboqs
- $ mkdir build && cd build 
- $ cmake -GNinja .. 
- $ cmake -GNinja .. -DBUILD_SHARED_LIBS=ON
- $ ninja
- $ sudo ninja install
- $ sudo ldconfig

# Using Kasa (https://github.com/python-kasa/python-kasa)
- $ pip install python-kasa

# Note on MAC:
- current_process.io_counters() doesn't work on Mac-OSX

# Creating large files with dd tool
- A file consisting of random bytes of size 1GB
$ dd if=/dev/urandom of=test.bin bs=1M count=1000


# Kasa Commands for TPLINK Smart Power Strip - HS300
- Getting all the socket aliases. There are 6 sockets on this power strip. 
$ kasa --verbose --host 192.168.11.105 --type strip device alias 

- Setting the alias/name of a specific socket on the strip to "rpi3b":
$ kasa --verbose --host 192.168.11.105 --type strip device alias --child-index 5 rpi3b

# Preparing Raspberry-Pis:
- Install pyenv on both raspberry-pis (https://github.com/pyenv/pyenv)
    - curl -fsSL https://pyenv.run | bash
    - Append the following ~/.bashrc
        export PYENV_ROOT="$HOME/.pyenv"
        [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
        eval "$(pyenv init - bash)"
    - reload the ~/.bashrc
        - $ source ~/.bashrc
- Install same version of python on both rpis:
    - $ pyenv install 3.10
- After new python is installed, set it to be used globally
    - $ pyenv versions
    - $ pyenv global 3.10

