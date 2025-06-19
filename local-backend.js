const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = 8000;

app.use(cors({
  origin: ['http://localhost:8000', 'http://127.0.0.1:8000'],
  credentials: true
}));

app.use(express.json());
app.use(express.static('.'));

const mockUser = {
  email: "test@shirushiru.com",
  roles: ["user"],
  tenant_id: "1"
};

let conversations = [
  {
    id: "conv-1",
    title: "サンプル会話",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  }
];

let messages = [];

app.post('/auth/login', (req, res) => {
  const { email, password } = req.body;
  
  if (email && password) {
    res.json({
      access_token: "mock-jwt-token",
      refresh_token: "mock-refresh-token",
      user: mockUser
    });
  } else {
    res.status(401).json({ error: "Invalid credentials" });
  }
});

app.post('/auth/refresh', (req, res) => {
  res.json({
    access_token: "mock-jwt-token-refreshed"
  });
});

app.post('/chat-messages', (req, res) => {
  const { query, response_mode, conversation_id, user, files } = req.body;
  
  if (response_mode === 'streaming') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Cache-Control'
    });

    const mockResponse = `こんにちは！「${query}」についてお答えします。これはローカル開発環境でのモック応答です。`;
    const words = mockResponse.split('');
    
    let index = 0;
    const streamInterval = setInterval(() => {
      if (index < words.length) {
        const chunk = {
          event: 'message',
          conversation_id: conversation_id || 'conv-' + Date.now(),
          message_id: 'msg-' + Date.now(),
          answer: words[index]
        };
        
        res.write(`data: ${JSON.stringify(chunk)}\n\n`);
        index++;
      } else {
        const finalChunk = {
          event: 'message_end',
          conversation_id: conversation_id || 'conv-' + Date.now(),
          message_id: 'msg-' + Date.now(),
          metadata: {
            retriever_resources: [
              {
                position: 1,
                dataset_id: "mock-dataset",
                dataset_name: "ローカルテストデータ",
                document_id: "mock-doc-1",
                document_name: "サンプル文書.pdf",
                content: "これはローカル開発環境でのサンプル引用です。"
              }
            ]
          }
        };
        
        res.write(`data: ${JSON.stringify(finalChunk)}\n\n`);
        res.end();
        clearInterval(streamInterval);
      }
    }, 50);

    req.on('close', () => {
      clearInterval(streamInterval);
    });
    
  } else {
    const mockResponse = {
      answer: `こんにちは！「${query}」についてお答えします。これはローカル開発環境でのブロッキングモード応答です。`,
      conversation_id: conversation_id || 'conv-' + Date.now(),
      message_id: 'msg-' + Date.now(),
      retriever_resources: [
        {
          position: 1,
          dataset_id: "mock-dataset",
          dataset_name: "ローカルテストデータ",
          document_id: "mock-doc-1", 
          document_name: "サンプル文書.pdf",
          content: "これはローカル開発環境でのサンプル引用です。"
        }
      ]
    };
    
    res.json(mockResponse);
  }
});

app.get('/files/detail', (req, res) => {
  const { docId } = req.query;
  res.json({
    id: docId,
    name: "サンプル文書.pdf",
    content: "これはローカル開発環境でのサンプル文書内容です。",
    created_at: new Date().toISOString()
  });
});

app.post('/files/upload', (req, res) => {
  res.json({
    id: "file-" + Date.now(),
    name: "アップロード済みファイル.pdf",
    status: "success"
  });
});

app.get('/conversation-list', (req, res) => {
  res.json({
    data: conversations,
    has_more: false
  });
});

app.get('/conversation-history', (req, res) => {
  const { conversation_id } = req.query;
  res.json({
    data: [
      {
        role: "user",
        content: "こんにちは",
        created_at: new Date().toISOString()
      },
      {
        role: "assistant", 
        content: "こんにちは！何かお手伝いできることはありますか？",
        created_at: new Date().toISOString()
      }
    ]
  });
});

app.get('/api-status', (req, res) => {
  res.json({
    status: "healthy",
    environment: "local-development",
    timestamp: new Date().toISOString()
  });
});

app.get('/app/api/tokens/balance', (req, res) => {
  res.json({
    balance: 1000,
    currency: "tokens",
    status: "active"
  });
});

app.post('/app/api/tokens/consume', (req, res) => {
  const { amount = 1 } = req.body;
  res.json({
    consumed: amount,
    remaining: 999,
    status: "success"
  });
});

app.get('/app/api/subscription/status', (req, res) => {
  res.json({
    status: "active",
    plan: "premium",
    expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
  });
});

app.use('/media', express.static(path.join(__dirname, 'media')));

app.listen(PORT, () => {
  console.log(`SHIRUSHIRU Local Backend Server running on http://localhost:${PORT}`);
  console.log('Environment: Local Development');
  console.log('API endpoints available:');
  console.log('  POST /auth/login');
  console.log('  POST /auth/refresh'); 
  console.log('  POST /chat-messages');
  console.log('  GET  /files/detail');
  console.log('  POST /files/upload');
  console.log('  GET  /conversation-list');
  console.log('  GET  /conversation-history');
  console.log('  GET  /api-status');
});
