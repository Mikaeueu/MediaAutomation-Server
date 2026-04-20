from flask import Flask

def create_app():
    app = Flask(__name__)

    app.config.from_object('app.config.Config')

    # importar rotas
    from app.routes.auth_routes import auth_bp
    from app.routes.obs_routes import obs_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(obs_bp)

    return app