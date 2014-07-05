#!/bin/bash

usage(){
    echo "usage:$0 [package [output_path]|unpackage <file>|clean|start [dev|deploy] [ini file]|reload|stop]"
}

check_deploy_env(){
    if [ -z "$DEPLOY" ];then
        echo "Not in deployment environment. Exiting..."
        exit 2
    fi
}

main(){
    case "$1" in
        package)
            PACKAGE_DIR=packages
            PACKAGE_NAME=`TZ='America/New York' date +%F_%H-%M-%S`.tar.gz
            PACKAGE_PATH=$PACKAGE_DIR/$PACKAGE_NAME
            [ ! -d ./packages ] && mkdir $PACKAGE_DIR
            tar zvc ./deploy.sh ./imods ./uwsgi.ini ./requirements.txt -f "${2-$PACKAGE_PATH}"
            echo ${2-$PACKAGE_PATH}
            ;;
        unpackage)
            if [ -z "$2" ];then
                usage
                return 1
            fi
            check_deploy_env
            tar zxv -C ~/app -f $2
            ;;
        clean)
            check_deploy_env
            rm -rf packages
            rm -rf ~/app/*
            ;;
        start)
            uwsgi --ini ${3-uwsgi.ini}:${2-dev}
            ;;
        reload)
            if [ ! -r /tmp/uwsgi_imods.pid ];then
                echo "uwsgi not started"
                return 0
            fi
            uwsgi --reload /tmp/uwsgi_imods.pid
            ;;
        stop)
            pkill -INT uwsgi
            ;;
        init)
            check_deploy_env
            cd ~/app
            echo "Creating virtualenv in ~/app..."
            virtualenv venv
            source venv/bin/activate
            echo "Installing packages using pip..."
            TEMP_REQUIREMENT_PATH=`mktemp`
            # Skip compiling and installing uwsgi, because it's slow
            # uwsgi should be already installed globally on the server
            grep -v 'uwsgi' requirements.txt > $TEMP_REQUIREMENT_PATH
            pip install -r $TEMP_REQUIREMENT_PATH
            rm $TEMP_REQUIREMENT_PATH
            ;;
        *) usage;;
    esac
}

main $*
