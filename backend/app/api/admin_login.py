# from typing import Any
# from backend.app.schemas import token
# from backend.app.core.security import create_access_token, create_refresh_token, verify_password
# from fastapi import APIRouter, Depends, HTTPException
# from fastapi.security import OAuth2PasswordRequestForm
# from common.app.db.api_db import get_user_by_email
#
# router = APIRouter()
#
#
# @router.post("/login/access-token", response_model=token.Token)
# async def login_access_token(
#         # db: Session = Depends(deps.get_db),
#         form_data: OAuth2PasswordRequestForm = Depends()
# ) -> Any:
#     """
#     OAuth2 compatible token login, get an access token for future requests
#     """
#     user = await get_user_by_email(form_data.username)
#     if user:
#         if not user.get("is_active"):
#             raise HTTPException(status_code=400, detail="Inactive user")
#         if verify_password(plain_password=form_data.password, hashed_password=user.get("hashed_password")):
#             # print(user)
#             return {
#                 "access_token": create_access_token(data={"sub": user.get("user_id")}),
#                 "refresh_token": create_refresh_token(data={"sub": user.get("user_id")}),
#                 "token_type": "bearer",
#             }
#
#     raise HTTPException(status_code=400, detail="Incorrect email or password")
#
