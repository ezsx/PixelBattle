from fastapi import APIRouter
import backend.app.api.admin_login as admin_login

def include_api(router: APIRouter):
    router.include_router(admin_login.router, prefix="/admin")
