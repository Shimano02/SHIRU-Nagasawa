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
  
  console.log('=== CHAT MESSAGE REQUEST RECEIVED ===');
  console.log('Query:', query);
  console.log('Response mode:', response_mode);
  console.log('Conversation ID:', conversation_id);
  console.log('User:', user);
  console.log('Files:', files);
  
  if (response_mode === 'streaming') {
    console.log('=== STARTING STREAMING MODE ===');
    
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.status(200);

    const convId = conversation_id || 'conv-' + Date.now();
    const msgId = 'msg-' + Date.now();
    
    console.log('=== SETTING UP STREAMING RESPONSE ===');
    console.log('Conversation ID:', convId);
    console.log('Message ID:', msgId);
    
    const fullResponse = `こんにちは！「${query}」についてお答えします。これはローカル開発環境でのストリーミング応答です。正常に動作しています。`;
    const characters = fullResponse.split('');
    let index = 0;
    
    console.log('=== CREATING STREAMING INTERVAL ===');
    console.log('Total characters to stream:', characters.length);
    
    console.log('=== ABOUT TO CREATE INTERVAL ===');
    
    console.log('=== TESTING IMMEDIATE EXECUTION ===');
    console.log('Response object state:', {
      headersSent: res.headersSent,
      finished: res.finished,
      destroyed: res.destroyed,
      writable: res.writable
    });
    
    try {
      const testChunk = { answer: "テ" };
      console.log('Sending immediate test chunk:', JSON.stringify(testChunk));
      res.write(`data: ${JSON.stringify(testChunk)}\n\n`);
      console.log('Immediate test chunk sent successfully');
    } catch (error) {
      console.error('Error sending immediate test chunk:', error);
      return;
    }
    
    console.log('=== TESTING DIRECT SETTIMEOUT ===');
    setTimeout(() => {
      console.log('=== SETTIMEOUT CALLBACK EXECUTED ===');
      console.log('This proves Node.js timers work');
    }, 100);
    
    console.log('=== SWITCHING TO IMMEDIATE STREAMING ===');
    
    function sendNextChunk() {
      console.log(`=== STREAMING CHUNK ${index} ===`);
      console.log('Current index:', index, 'Total characters:', characters.length);
      
      if (index < characters.length) {
        const chunk = {
          answer: characters[index]
        };
        
        console.log('Sending chunk:', JSON.stringify(chunk));
        try {
          res.write(`data: ${JSON.stringify(chunk)}\n\n`);
          console.log('Chunk sent successfully');
          index++;
          
          setTimeout(sendNextChunk, 50);
        } catch (error) {
          console.error('Error writing chunk:', error);
          return;
        }
      } else {
        console.log('=== SENDING FINAL CHUNK AND DONE ===');
        const finalChunk = {
          conversation_id: convId,
          message_id: msgId,
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
        
        console.log('Sending final chunk:', JSON.stringify(finalChunk));
        try {
          res.write(`data: ${JSON.stringify(finalChunk)}\n\n`);
          console.log('Sending [DONE] marker');
          res.write(`data: [DONE]\n\n`);
          console.log('Ending response and clearing interval');
          res.end();
        } catch (error) {
          console.error('Error writing final chunk:', error);
        }
      }
    }
    
    setTimeout(sendNextChunk, 50);
    
    console.log('=== RECURSIVE TIMEOUT STARTED ===');

    req.on('close', () => {
      console.log('Request closed - streaming will stop naturally');
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
