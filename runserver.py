import os
from biome import app

if __name__ == '__main__':
    app.config['SECRET_KEY'] = 'secret_key_from_env'
    UPLOAD_FOLDER = 'biome/data_files'
    app.config['UPLOAD_FOLDER'] = os.getcwd()+'/'+UPLOAD_FOLDER

    app.run(host='0.0.0.0', port=7777, debug=True, use_reloader=True)
