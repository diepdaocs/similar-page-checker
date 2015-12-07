# Web pages similarity checking #
## Install python environment libraries for Ubuntu ##
```
#!shell
sudo apt-get install -y git python-dev python-pip build-essential libxml2-dev libxslt1-dev zlib1g-dev python3-pip
sudo pip install virtualenvwrapper
source `which virtualenvwrapper.sh` && echo "source `which virtualenvwrapper.sh`" >> ~/.bashrc && echo "[[ -r ~/.bashrc ]] && . ~/.bashrc" >> ~/.bash_profile

```
## Install python project virtual environment ##
Create virtual environment
```
#!shell
mkvirtualenv webpages-duplicated-checking

```
Active virtual environment (Remember to active virtual environment before run service)
```
#!shell
workon webpages-duplicated-checking

```
## Get source code and install requirements into virtual environment ##

```
#!shell
git clone https://diepdt@bitbucket.org/diepdt/webpages-duplicated-checking.git
cd webpages-duplicated-checking/
workon webpages-duplicated-checking
pip install -r requirements.txt

```
## Run webpages-duplicated-checking service ##
```
#!shell
cd webpages-duplicated-checking/
screen -R webpages-duplicated-checking
workon webpages-duplicated-checking
python main.py

```
## Monitor and view service logs ##
```
#!shell
screen -r webpages-duplicated-checking

```
To stop service, press Ctrl + C.
To start service:
```
#!shell
workon webpages-duplicated-checking
python main.py

```