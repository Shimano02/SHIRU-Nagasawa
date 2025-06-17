from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import httpx
import json
import os
import uuid
import asyncio
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import aiofiles
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SHIRUSHIRU AI Secretary API", version="1.0.0")

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

DIFY_API_KEY = os.getenv("DIFY_API_KEY", "")
DIFY_BASE_URL = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")
DIFY_APP_ID = os.getenv("DIFY_APP_ID", "")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_secret_key_change_in_production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

users_db = {}
conversations_db = {}
files_db = {}
tokens_db = {}

class UserLogin(BaseModel):
    email: EmailStr
    password: Optional[str] = None

class ChatMessage(BaseModel):
    inputs: Dict[str, Any] = {}
    query: str
    response_mode: str = "streaming"
    conversation_id: Optional[str] = None
    user: str = "guest"
    files: List[Dict[str, Any]] = []

class ConversationCreate(BaseModel):
    user: str

class FileUpdate(BaseModel):
    docId: str
    content: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserInfo(BaseModel):
    email: str
    roles: List[str] = []
    tenant: str = "1"
    token_balance: int = 1000

class LoginResponse(BaseModel):
    access: str
    refresh: str
    user: UserInfo

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    email = verify_token(token)
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return email

async def call_dify_chat_api_streaming(message_data: dict):
    """Call Dify Chat API for streaming responses"""
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    dify_payload = {
        "inputs": message_data.get("inputs", {}),
        "query": message_data["query"],
        "response_mode": "streaming",
        "conversation_id": message_data.get("conversation_id", ""),
        "user": message_data.get("user", "guest"),
        "files": message_data.get("files", [])
    }
    
    if not DIFY_API_KEY or DIFY_API_KEY == "your_dify_api_key_here":
        user_query = message_data.get("query", "")
        mock_response = f"こんにちは！SHIRUSHIRU AI秘書です。「{user_query}」についてお答えします。\n\n"
        
        if "時間" in user_query or "時刻" in user_query:
            mock_response += f"現在の時刻は{datetime.now().strftime('%Y年%m月%d日 %H時%M分')}です。"
        elif "天気" in user_query:
            mock_response += "申し訳ございませんが、リアルタイムの天気情報を取得するには外部APIとの連携が必要です。"
        elif "翻訳" in user_query:
            mock_response += "翻訳機能をご利用いただきありがとうございます。本格運用時には高精度な翻訳サービスを提供いたします。"
        elif "ファイル" in user_query or "文書" in user_query:
            mock_response += "ファイル管理機能は実装済みです。アップロード、検索、編集が可能です。"
        else:
            mock_response += "現在、Dify APIの設定が完了していないため、テスト応答を返しています。本格運用時には、より詳細で正確な情報をご提供いたします。"
        
        words = mock_response.split()
        current_text = ""
        for word in words:
            current_text += word + " "
            chunk_data = {
                "event": "message",
                "message_id": str(uuid.uuid4()),
                "conversation_id": message_data.get("conversation_id", ""),
                "answer": current_text.strip(),
                "created_at": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"
            await asyncio.sleep(0.05)  # Simulate realistic typing speed
        
        final_data = {
            "event": "message_end",
            "message_id": str(uuid.uuid4()),
            "conversation_id": message_data.get("conversation_id", ""),
            "answer": mock_response,
            "created_at": datetime.utcnow().isoformat()
        }
        yield f"data: {json.dumps(final_data)}\n\n"
        return
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{DIFY_BASE_URL}/chat-messages",
            headers=headers,
            json=dify_payload
        ) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"Dify API error: {response.status_code} - {error_text}")
                raise HTTPException(status_code=response.status_code, detail="Dify API error")
            
            async for chunk in response.aiter_text():
                if chunk.strip():
                    yield chunk

async def call_dify_chat_api_blocking(message_data: dict):
    """Call Dify Chat API for blocking responses"""
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    dify_payload = {
        "inputs": message_data.get("inputs", {}),
        "query": message_data["query"],
        "response_mode": "blocking",
        "conversation_id": message_data.get("conversation_id", ""),
        "user": message_data.get("user", "guest"),
        "files": message_data.get("files", [])
    }
    
    if not DIFY_API_KEY:
        return {
            "message_id": str(uuid.uuid4()),
            "conversation_id": str(uuid.uuid4()),
            "answer": "申し訳ございませんが、現在Dify APIが設定されていません。テスト用の応答です。",
            "created_at": datetime.utcnow().isoformat()
        }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{DIFY_BASE_URL}/chat-messages",
            headers=headers,
            json=dify_payload
        )
        if response.status_code != 200:
            logger.error(f"Dify API error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Dify API error")
        
        return response.json()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/api-status")
async def api_status():
    return {
        "status": "ok",
        "api_checks": {
            "parameters": {
                "status": "ok"
            }
        },
        "dify_connection": bool(DIFY_API_KEY),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/ping")
async def ping():
    return {"message": "pong", "timestamp": datetime.utcnow().isoformat()}

@app.post("/auth/login", response_model=LoginResponse)
async def login(user_data: UserLogin):
    email = user_data.email
    
    if email not in users_db:
        users_db[email] = {
            "email": email,
            "roles": ["西村製作_社員"],  # Default role
            "tenant": "1",
            "token_balance": 1000,
            "created_at": datetime.utcnow()
        }
    
    access_token = create_access_token(data={"sub": email})
    refresh_token = create_refresh_token(data={"sub": email})
    
    tokens_db[email] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "created_at": datetime.utcnow()
    }
    
    user_info = users_db[email]
    
    return LoginResponse(
        access=access_token,
        refresh=refresh_token,
        user=UserInfo(
            email=email,
            roles=user_info.get("roles", ["西村製作_社員"]),
            tenant=user_info.get("tenant", "1"),
            token_balance=user_info.get("token_balance", 1000)
        )
    )

@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    email = verify_token(refresh_token)
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    access_token = create_access_token(data={"sub": email})
    new_refresh_token = create_refresh_token(data={"sub": email})
    
    tokens_db[email] = {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "created_at": datetime.utcnow()
    }
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token
    )

@app.get("/app/api/tokens/balance")
async def get_token_balance(current_user: str = Depends(get_current_user)):
    user_info = users_db.get(current_user, {})
    return {
        "balance": user_info.get("token_balance", 1000),
        "user": current_user
    }

@app.post("/app/api/tokens/consume")
async def consume_tokens(
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """Consume tokens for API usage"""
    try:
        tokens_to_consume = request.get("tokens", 1)
        user_info = users_db.get(current_user, {})
        current_balance = user_info.get("token_balance", 1000)
        
        if current_balance >= tokens_to_consume:
            new_balance = current_balance - tokens_to_consume
            if current_user not in users_db:
                users_db[current_user] = {"token_balance": 1000}
            users_db[current_user]["token_balance"] = new_balance
            
            return {
                "success": True,
                "consumed": tokens_to_consume,
                "remaining_balance": new_balance
            }
        else:
            raise HTTPException(status_code=400, detail="Insufficient token balance")
            
    except Exception as e:
        logger.error(f"Token consumption error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/profile")
async def get_user_profile(current_user: str = Depends(get_current_user)):
    user_info = users_db.get(current_user, {})
    return UserInfo(
        email=current_user,
        roles=user_info.get("roles", ["西村製作_社員"]),
        tenant=user_info.get("tenant", "1"),
        token_balance=user_info.get("token_balance", 1000)
    )

@app.post("/chat-messages")
async def chat_messages(
    message: ChatMessage,
    current_user: str = Depends(get_current_user)
):
    """Main chat endpoint with streaming/blocking support"""
    try:
        message.user = current_user
        
        message_data = message.dict()
        
        if message.response_mode == "streaming":
            async def generate_stream():
                try:
                    async for chunk in call_dify_chat_api_streaming(message_data):
                        yield chunk
                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return StreamingResponse(generate_stream(), media_type="text/event-stream")
        else:
            result = await call_dify_chat_api_blocking(message_data)
            return result
            
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation-list")
async def get_conversation_list(
    user: str,
    current_user: str = Depends(get_current_user)
):
    """Get user's conversation list"""
    user_conversations = conversations_db.get(user, [])
    return {
        "data": user_conversations,
        "total": len(user_conversations)
    }

@app.post("/conversations/new")
async def create_new_conversation(
    conversation: ConversationCreate,
    current_user: str = Depends(get_current_user)
):
    """Create a new conversation"""
    conversation_id = str(uuid.uuid4())
    new_conversation = {
        "id": conversation_id,
        "name": f"会話 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "created_at": datetime.utcnow().isoformat(),
        "user": conversation.user,
        "messages": []
    }
    
    if conversation.user not in conversations_db:
        conversations_db[conversation.user] = []
    
    conversations_db[conversation.user].append(new_conversation)
    
    return {
        "success": True,
        "conversation_id": conversation_id,
        "data": new_conversation
    }

@app.get("/conversation-history")
async def get_conversation_history(
    user: str,
    conversation_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get conversation message history"""
    user_conversations = conversations_db.get(user, [])
    conversation = next((c for c in user_conversations if c["id"] == conversation_id), None)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "data": conversation["messages"],
        "conversation_name": conversation["name"]
    }

@app.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    data: str = Form(...),
    current_user: str = Depends(get_current_user)
):
    """Upload file and register to knowledge base"""
    try:
        metadata = json.loads(data)
        
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")
        
        file_id = str(uuid.uuid4())
        
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        file_record = {
            "id": file_id,
            "document_id": file_id,  # Use same ID for document
            "filename": file.filename,
            "file_path": file_path,
            "file_size": file_size,
            "content_type": file.content_type,
            "uploaded_by": current_user,
            "uploaded_at": datetime.utcnow().isoformat(),
            "metadata": metadata,
            "segments": []  # Will be populated when processing
        }
        
        files_db[file_id] = file_record
        
        return {
            "success": True,
            "document_id": file_id,
            "filename": file.filename,
            "message": "ファイルがアップロードされました"
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid metadata format")
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/detail")
async def get_file_detail(
    docId: str,
    current_user: str = Depends(get_current_user)
):
    """Get file content for citation details"""
    file_record = files_db.get(docId)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        async with aiofiles.open(file_record["file_path"], 'r', encoding='utf-8') as f:
            content = await f.read()
        
        segments = [
            {
                "segment_id": "1",
                "content": content[:1000] + "..." if len(content) > 1000 else content
            }
        ]
        
        return {
            "data": segments
        }
        
    except Exception as e:
        logger.error(f"File detail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/update")
async def update_file(
    file_update: FileUpdate,
    current_user: str = Depends(get_current_user)
):
    """Update file content"""
    file_record = files_db.get(file_update.docId)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        async with aiofiles.open(file_record["file_path"], 'w', encoding='utf-8') as f:
            await f.write(file_update.content)
        
        file_record["updated_at"] = datetime.utcnow().isoformat()
        file_record["updated_by"] = current_user
        
        return {
            "success": True,
            "message": "ファイルが更新されました"
        }
        
    except Exception as e:
        logger.error(f"File update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/datasets/{dataset_id}/documents/{doc_id}")
async def delete_file(
    dataset_id: str,
    doc_id: str,
    current_user: str = Depends(get_current_user)
):
    """Delete file from knowledge base"""
    file_record = files_db.get(doc_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        if os.path.exists(file_record["file_path"]):
            os.remove(file_record["file_path"])
        
        del files_db[doc_id]
        
        return {
            "success": True,
            "message": "ファイルが削除されました"
        }
        
    except Exception as e:
        logger.error(f"File delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/media/")
async def get_media_list(current_user: str = Depends(get_current_user)):
    """Get media file list"""
    media_files = [
        {
            "id": file_id,
            "title": record["filename"],
            "content": record.get("metadata", {}).get("description", ""),
            "created_at": record["uploaded_at"],
            "file_type": record["content_type"]
        }
        for file_id, record in files_db.items()
    ]
    
    return {
        "results": media_files,
        "total": len(media_files)
    }

@app.post("/media/")
async def create_knowledge_entry(
    title: str = Form(...),
    content: str = Form(""),
    tenant: str = Form("1"),
    attached_file: Optional[UploadFile] = File(None),
    current_user: str = Depends(get_current_user)
):
    """Create knowledge base entry"""
    try:
        entry_id = str(uuid.uuid4())
        
        file_path = None
        if attached_file:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            file_path = os.path.join(UPLOAD_DIR, f"{entry_id}_{attached_file.filename}")
            content_bytes = await attached_file.read()
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content_bytes)
        
        knowledge_entry = {
            "id": entry_id,
            "title": title,
            "content": content,
            "tenant": tenant,
            "file_path": file_path,
            "filename": attached_file.filename if attached_file else None,
            "created_by": current_user,
            "created_at": datetime.utcnow().isoformat()
        }
        
        files_db[entry_id] = knowledge_entry
        
        return {
            "success": True,
            "id": entry_id,
            "message": "ナレッジが登録されました"
        }
        
    except Exception as e:
        logger.error(f"Knowledge creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/text-to-audio")
async def text_to_audio(
    request: dict,
    current_user: str = Depends(get_current_user)
):
    """Convert text to audio using TTS"""
    try:
        text = request.get("text", "")
        user = request.get("user", current_user)
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        audio_url = f"https://example.com/audio/{uuid.uuid4()}.mp3"
        
        return {
            "success": True,
            "audio_url": audio_url,
            "duration": len(text) * 0.1,  # Mock duration
            "message": "音声が生成されました"
        }
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/audio-to-text")
async def audio_to_text(
    audio_file: UploadFile = File(...),
    current_user: str = Depends(get_current_user)
):
    """Convert audio to text using STT"""
    try:
        
        return {
            "success": True,
            "text": "これは音声認識のテスト結果です。",
            "confidence": 0.95,
            "message": "音声が認識されました"
        }
        
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/suggested-questions")
async def get_suggested_questions(
    message_id: str,
    user: str,
    current_user: str = Depends(get_current_user)
):
    """Get suggested follow-up questions"""
    try:
        suggestions = [
            "詳しく教えてください",
            "他の方法はありますか？",
            "具体例を教えてください",
            "関連する情報はありますか？"
        ]
        
        return {
            "data": suggestions,
            "message_id": message_id
        }
        
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/list")
async def get_file_list(current_user: str = Depends(get_current_user)):
    """Get user's uploaded files list"""
    user_files = [
        {
            "id": file_id,
            "document_id": record["document_id"],
            "filename": record["filename"],
            "uploaded_at": record["uploaded_at"],
            "file_size": record["file_size"],
            "content_type": record["content_type"]
        }
        for file_id, record in files_db.items()
        if record.get("uploaded_by") == current_user
    ]
    
    return {
        "data": user_files,
        "total": len(user_files)
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
