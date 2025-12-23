<template>
  <GlassCard no-padding class="h-full">
    <div class="h-full flex flex-col relative">
      <div
        class="flex-none h-14 px-5 border-b border-white/5 bg-white/2 backdrop-blur-sm flex justify-between items-center z-20">
        <div class="flex items-center gap-2">
          <div class="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-glow-cyan"></div>
          <span class="text-xs font-medium text-gray-400 tracking-wide">
            CONTEXT: <span class="text-cyan-300 font-mono">{{ selectedTaskId }}</span>
          </span>
        </div>
        <StatusDot :status="aiStatus" size="sm" :label="aiStatusLabel" />
      </div>

      <div ref="messagesContainer"
        class="messages-container flex-1 overflow-y-auto p-5 space-y-6 scroll-smooth pb-[88px]" @scroll="handleScroll">
        <!-- Welcome message -->
        <div v-if="messages.length === 0"
          class="flex flex-col items-center justify-center h-full pb-10 opacity-0 animate-[fade-in_0.5s_ease-out_forwards]">
          <h3
            class="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 to-blue-300 mb-2 glow-text-cyan">
            System Copilot
          </h3>
          <p class="text-sm text-gray-400 max-w-md text-center">
            I'm your AI assistant for data pipeline management. Ask me questions, run commands, or get help with your
            tasks.
          </p>
          <div class="mt-6 flex gap-2 flex-wrap justify-center">
            <button @click="executeCommand('help')"
              class="px-3 py-1.5 text-xs bg-cyan-400/20 hover:bg-cyan-400/30 border border-cyan-400/30 rounded-full text-cyan-300 transition-colors">
              Get Started
            </button>
            <button @click="executeCommand('status')"
              class="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-gray-300 transition-colors">
              Check Status
            </button>
          </div>
        </div>

        <!-- AI Thinking Process -->
        <div v-if="aiStatus === 'thinking' && aiThinkingText" class="flex gap-3">
          <div
            class="w-8 h-8 rounded-full flex items-center justify-center border text-xs bg-cyan-400/20 border-cyan-400/30">
            AI
          </div>
          <div class="flex flex-col gap-1 max-w-[85%]">
            <div
              class="border rounded-2xl p-3 text-sm text-gray-200 leading-relaxed shadow-sm bg-white/5 border-white/10 rounded-tl-none">
              <div class="flex items-center gap-2">
                <span class="text-cyan-300 animate-pulse">Thinking</span>
                <svg class="animate-spin -ml-1 mr-1 h-3 w-3 text-cyan-300" xmlns="http://www.w3.org/2000/svg"
                  fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                  </path>
                </svg>
              </div>
              <div class="mt-2 text-sm text-gray-400 italic">
                {{ aiThinkingText }}
              </div>
            </div>
          </div>
        </div>

        <!-- Messages -->
        <div v-for="message in messages" :key="message.id" class="flex gap-3"
          :class="{ 'flex-row-reverse': message.role === 'user' }">
          <div :class="[
            'w-8 h-8 rounded-full flex items-center justify-center border text-xs',
            message.role === 'ai'
              ? 'bg-cyan-400/20 border-cyan-400/30'
              : 'bg-gray-700/50 border-white/10',
            message.status === 'error' ? 'border-red-500 bg-red-500/20' : ''
          ]">
            {{ message.role === 'ai' ? 'AI' : 'Me' }}
          </div>
          <div :class="[
            'flex flex-col gap-1 max-w-[85%]',
            message.role === 'user' ? 'items-end' : 'items-start'
          ]">
            <div :class="[
              'border rounded-2xl p-3 text-sm text-gray-200 leading-relaxed shadow-sm',
              message.role === 'ai'
                ? 'bg-white/5 border-white/10 rounded-tl-none'
                : 'bg-cyan-400/10 border-cyan-400/20 rounded-tr-none',
              message.status === 'loading' ? 'animate-pulse/20' : '',
              message.status === 'error' ? 'border-red-500 bg-red-500/10 text-red-300' : ''
            ]">
              <span v-if="message.type === 'command'"
                class="inline-block bg-cyan-400/20 text-cyan-300 text-xs px-2 py-0.5 rounded mr-2 mb-1">
                Command
              </span>
              <div v-if="message.status === 'loading'" class="flex items-center gap-2">
                <span class="text-cyan-300 animate-pulse">Thinking</span>
                <svg class="animate-spin -ml-1 mr-1 h-3 w-3 text-cyan-300" xmlns="http://www.w3.org/2000/svg"
                  fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                  </path>
                </svg>
              </div>
              <div v-else-if="message.status === 'error'" class="flex flex-col gap-2">
                <div class="flex items-center gap-2">
                  <svg class="w-4 h-4 text-red-400" fill="currentColor" viewBox="0 0 24 24">
                    <path
                      d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" />
                  </svg>
                  <span class="font-medium">Error</span>
                </div>
                <div>{{ message.content }}</div>
                <button @click="retryMessage(message)"
                  class="self-start px-2 py-1 text-xs bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded text-red-300 transition-colors">
                  Retry
                </button>
              </div>
              <div v-else v-html="renderMarkdown(message.content)" class="markdown-content"></div>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] text-gray-600" :class="message.role === 'user' ? 'pr-1' : 'pl-1'">
                {{ formatTime(message.timestamp) }}
              </span>
              <span v-if="message.role === 'user'" class="flex items-center gap-1">
                <svg v-if="message.status === 'sent'" class="w-2.5 h-2.5 text-cyan-300" fill="currentColor"
                  viewBox="0 0 16 16">
                  <path
                    d="M15 3a1 1 0 0 1-1 1H2a1 1 0 0 1 0-2h12a1 1 0 0 1 1 1zm0 10a1 1 0 0 1-1 1H2a1 1 0 0 1 0-2h12a1 1 0 0 1 1 1zm-3 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0z" />
                </svg>
                <svg v-else-if="message.status === 'delivered'" class="w-2.5 h-2.5 text-green-400" fill="currentColor"
                  viewBox="0 0 16 16">
                  <path
                    d="M15 3a1 1 0 0 1-1 1H2a1 1 0 0 1 0-2h12a1 1 0 0 1 1 1zm0 10a1 1 0 0 1-1 1H2a1 1 0 0 1 0-2h12a1 1 0 0 1 1 1zm-3 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0z" />
                </svg>
                <svg v-else-if="message.status === 'error'" class="w-2.5 h-2.5 text-red-500" fill="currentColor"
                  viewBox="0 0 16 16">
                  <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z" />
                  <path
                    d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z" />
                </svg>
                <svg v-else class="w-2.5 h-2.5 text-gray-500 animate-pulse" fill="currentColor" viewBox="0 0 16 16">
                  <path
                    d="M15 3a1 1 0 0 1-1 1H2a1 1 0 0 1 0-2h12a1 1 0 0 1 1 1zm0 10a1 1 0 0 1-1 1H2a1 1 0 0 1 0-2h12a1 1 0 0 1 1 1zm-3 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0z" />
                </svg>
                <span :class="[
                  'text-[10px]',
                  message.status === 'sent' ? 'text-cyan-300' :
                    message.status === 'delivered' ? 'text-green-400' :
                      message.status === 'error' ? 'text-red-500' : 'text-gray-500'
                ]">
                  {{ message.status === 'sent' ? 'Sent' :
                    message.status === 'delivered' ? 'Delivered' :
                      message.status === 'error' ? 'Failed' : 'Sending...' }}
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Scroll to bottom button -->
      <button v-if="showScrollToBottom" @click="scrollToBottom"
        class="absolute bottom-24 right-6 bg-cyan-400/80 hover:bg-cyan-400 text-white rounded-full w-9 h-9 flex items-center justify-center shadow-lg transition-all z-10 animate-bounce"
        :class="showScrollToBottom ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4 pointer-events-none'"
        title="Scroll to bottom">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path>
        </svg>
      </button>

      <!-- Input HUD - Absolute positioned at bottom -->
      <div class="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-[#030508]/80 to-transparent z-20">
        <div v-if="showCommandMenu"
          class="absolute bottom-20 left-4 right-4 bg-gray-800/95 border border-white/10 rounded-lg shadow-xl z-20 max-h-60 overflow-y-auto">
          <div v-for="command in filteredCommands" :key="command.name"
            class="px-4 py-3 hover:bg-white/5 cursor-pointer transition-colors text-sm"
            @click="executeCommand(command.name)">
            <div class="flex justify-between items-center">
              <span class="text-cyan-300">{{ command.name }}</span>
              <span class="text-gray-500 text-xs">{{ command.description }}</span>
            </div>
            <div v-if="command.example" class="text-[10px] text-gray-600 mt-1">
              Example: {{ command.example }}
            </div>
          </div>
          <div v-if="filteredCommands.length === 0" class="px-4 py-3 text-gray-500 text-sm">
            No matching commands found
          </div>
        </div>

        <InputHud v-model="input" :loading="aiStatus === 'thinking'" placeholder="Ask Copilot..."
          @input="handleInputChange" @submit="handleSend" @keydown.enter="handleSend" class="w-full shadow-hud-focus" />
      </div>
    </div>
  </GlassCard>
</template>

<script setup>
import { ref, onMounted, nextTick, computed, watch, onUnmounted, } from 'vue';
import GlassCard from '@/components/ui/GlassCard.vue';
import InputHud from '@/components/ui/InputHud.vue';
import StatusDot from '@/components/ui/StatusDot.vue';
import { sendUserMessage } from '../../api/order';
import { useConversationSSE } from '../../composables/useApi';
import MarkdownIt from 'markdown-it';
import DOMPurify from 'dompurify';

// 接收选中的任务ID
const props = defineProps({
  selectedTaskId: {
    type: String,
    required: true
  }
});

const input = ref('');
const messagesContainer = ref(null)
const showCommandMenu = ref(false);
const commandPrefix = ref('');
const showScrollToBottom = ref(false);
const sessionId = ref('default-session');
const currentAIMessage = ref(null);

const messages = ref([]);
const aiStatus = ref('idle'); // idle, thinking, processing
const aiThinkingText = ref(''); // 新增：用于显示具体的思考步骤

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true
});

const renderMarkdown = (text) => {
  if (!text) return '';
  const html = md.render(text);
  return DOMPurify.sanitize(html);
};

// 使用 SSE 组合函数连接对话流
const {
  sseClient,
  isConnected,
  events,
  initializeSSE,
  disconnect
} = useConversationSSE(sessionId.value, {
  // 确保这里监听了所有后端发出的事件名
  events: ['thought', 'done', 'error'],

  onOpen: () => {
    console.log('SSE connected');
    aiStatus.value = 'idle';
  },

  onMessage: (data, event) => {
    // 处理 SSE 消息
    let parsedData = data;
    if (typeof data === 'string') {
      try {
        parsedData = JSON.parse(data);
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
        return;
      }
    }

    // 2. 区分处理 'thought' 事件 (根据数据结构包含 message 且不含 content)
    // 后端格式: event: thought, data: {"message": "..."}
    if (parsedData.message && !parsedData.content) {
      aiStatus.value = 'thinking';
      // 可以选择显示这个思考过程，或者仅仅作为状态更新
      aiThinkingText.value = parsedData.message;
      console.log('AI Thought:', parsedData.message);
      return; // ⛔️ 这里的 return 很重要，防止思考过程进入下面的对话追加逻辑
    }

    // 3. 区分处理 'message' 事件 (正式内容)
    // 后端格式: event: message, data: {"content": "..."}
    if (parsedData.chunk !== undefined || parsedData.content !== undefined) {
      aiStatus.value = 'processing';
      const chunk = parsedData.chunk || parsedData.content;

      if (!currentAIMessage.value) {
        // 创建新的 AI 消息
        currentAIMessage.value = {
          id: Date.now(),
          role: 'ai',
          content: '',
          timestamp: new Date(),
          status: 'processing'
        };
        messages.value.push(currentAIMessage.value);
        scrollToBottom();
      }

      // 追加内容
      currentAIMessage.value.content += chunk;
      scrollToBottom();
    }
  },
  onDone: (data) => {
    console.log('SSE done event:', data);
    aiStatus.value = 'idle';
    aiThinkingText.value = ''; // 清空思考文字
    if (currentAIMessage.value) {
      currentAIMessage.value.status = 'completed';
      currentAIMessage.value = null;
    }
  },
  onError: (error) => {
    console.error('SSE error:', error);
    aiStatus.value = 'idle';

    // 添加错误消息
    const errorMessage = {
      id: Date.now(),
      role: 'ai',
      content: error.error || 'An error occurred while processing your request.',
      timestamp: new Date(),
      status: 'error'
    };

    if (currentAIMessage.value) {
      currentAIMessage.value.status = 'error';
      currentAIMessage.value.content = errorMessage.content;
      currentAIMessage.value = null;
    } else {
      messages.value.push(errorMessage);
    }

    scrollToBottom();
  }
});


// !!! 关键修复 1：组件卸载时强制断开连接 !!!
onUnmounted(() => {
  console.log('Component unmounting: Disconnecting SSE to prevent ghost connections.');
  disconnect();
});

// !!! 关键修复 2：监听 Session ID 变化时的清理逻辑 !!!
watch(sessionId, async (newSessionId) => {
  // 先断开旧连接
  disconnect();
  // 重置当前 AI 消息状态，防止旧数据污染
  currentAIMessage.value = null;
  aiStatus.value = 'idle';

  await nextTick();

  // 再建立新连接
  initializeSSE();
});

// !!! 关键修复 3：挂载时的防御性连接 !!!
onMounted(() => {
  scrollToBottom();

  // 先尝试断开可能存在的残留连接（防止热更新导致的重复）
  disconnect();

  // 稍微延迟一下再连接，确保之前的 socket 完全关闭
  setTimeout(() => {
    initializeSSE();
  }, 100);
});

const aiStatusLabel = computed(() => {
  switch (aiStatus.value) {
    case 'thinking': return 'Thinking...';
    case 'processing': return 'Processing...';
    default: return 'AI Ready';
  }
});

const commands = [
  {
    name: '/help',
    description: 'Show available commands',
    example: '/help'
  },
  {
    name: '/clear',
    description: 'Clear all messages',
    example: '/clear'
  },
  {
    name: '/status',
    description: 'Show current system status',
    example: '/status'
  },
  {
    name: '/tasks',
    description: 'Show active tasks',
    example: '/tasks'
  },
  {
    name: '/log',
    description: 'Show recent logs',
    example: '/log'
  },
  {
    name: '/config',
    description: 'Show configuration',
    example: '/config'
  }
];

const filteredCommands = computed(() => {
  if (!commandPrefix.value) return commands;
  return commands.filter(cmd =>
    cmd.name.toLowerCase().includes(commandPrefix.value.toLowerCase())
  );
});

const formatTime = (date) => {
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
};

const scrollToBottom = async () => {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    showScrollToBottom.value = false;
  }
};

const handleScroll = () => {
  if (!messagesContainer.value) return;

  const { scrollTop, scrollHeight, clientHeight } = messagesContainer.value;
  const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
  showScrollToBottom.value = !isNearBottom;
};

const handleInputChange = () => {
  if (input.value.startsWith('/')) {
    showCommandMenu.value = true;
    commandPrefix.value = input.value.slice(1);
  } else {
    showCommandMenu.value = false;
  }
};

const handleSend = async () => {
  if (!input.value.trim()) return;

  showCommandMenu.value = false;

  // Check if it's a command
  if (input.value.startsWith('/')) {
    executeCommand(input.value);
    return;
  }

  const newMessage = {
    id: Date.now(),
    role: 'user',
    content: input.value.trim(),
    timestamp: new Date(),
    status: 'sending'
  };

  messages.value.push(newMessage);
  input.value = '';
  aiStatus.value = 'thinking';

  scrollToBottom();

  try {
    // 更新消息状态为发送中
    newMessage.status = 'sending';

    // 调用真实 API 发送消息
    await sendUserMessage(sessionId.value, {
      utterance: newMessage.content,
      timestamp: Date.now(),
      metadata: {
        taskId: props.selectedTaskId,
        sessionId: sessionId.value
      }
    });

    // 更新消息状态为已发送
    newMessage.status = 'sent';

    setTimeout(() => {
      newMessage.status = 'delivered';
    }, 500);

    // AI 响应将通过 SSE 接收
    aiStatus.value = 'processing';
  } catch (error) {
    console.error('Failed to send message:', error);
    newMessage.status = 'error';
    aiStatus.value = 'idle';

    // 添加错误提示
    const errorMessage = {
      id: Date.now() + 1,
      role: 'ai',
      content: `An error occurred while sending your message: ${error.message}`,
      timestamp: new Date(),
      status: 'error'
    };

    messages.value.push(errorMessage);
    scrollToBottom();
  }
};

const executeCommand = (command) => {
  let commandName = command.startsWith('/') ? command.slice(1) : command;
  input.value = '';
  showCommandMenu.value = false;

  // Add command message to chat
  const commandMessage = {
    id: Date.now(),
    role: 'user',
    content: `/${commandName}`,
    timestamp: new Date(),
    status: 'completed',
    type: 'command'
  };

  messages.value.push(commandMessage);
  aiStatus.value = 'processing';
  scrollToBottom();

  // Execute command logic
  setTimeout(() => {
    const aiResponse = {
      id: Date.now() + 1,
      role: 'ai',
      content: getCommandResponse(commandName),
      timestamp: new Date(),
      status: 'completed'
    };

    messages.value.push(aiResponse);
    aiStatus.value = 'idle';
    scrollToBottom();
  }, 1000);
};

const getCommandResponse = (commandName) => {
  switch (commandName.toLowerCase()) {
    case 'help':
      return 'Available commands:\n' +
        commands.map(cmd => `• ${cmd.name} - ${cmd.description}`).join('\n');
    case 'clear':
      messages.value = [];
      return 'Chat history cleared successfully.';
    case 'status':
      return 'System Status:\n' +
        '• AI Service: Online\n' +
        '• Tasks: 3 active (TSK-01, TSK-02, TSK-03)\n' +
        '• Nodes: 8/8 healthy\n' +
        '• Version: v1.2.3';
    case 'tasks':
      return 'Active Tasks:\n' +
        '• TSK-01: Data Ingestion Pipeline (50% complete)\n' +
        '• TSK-02: Model Training (75% complete)\n' +
        '• TSK-03: Report Generation (20% complete)';
    case 'log':
      return 'Recent Logs:\n' +
        '[10:45 AM] INFO: Data ingestion started\n' +
        '[10:46 AM] WARN: Schema mismatch detected\n' +
        '[10:47 AM] INFO: AI analysis completed\n' +
        '[10:48 AM] DEBUG: Connection established';
    case 'config':
      return 'Configuration:\n' +
        '• Context: TSK-01\n' +
        '• AI Model: GPT-4 Turbo\n' +
        '• Temperature: 0.7\n' +
        '• Max Tokens: 2048';
    default:
      return `Unknown command: /${commandName}. Type /help for available commands.`;
  }
};

const generateAIResponse = (userMessage) => {
  // Simple response generation logic
  const responses = [
    `I've analyzed your request: "${userMessage}". Let me help you with that.`,
    `Based on your input "${userMessage}", here's what I recommend...`,
    `Thank you for your message: "${userMessage}". I'll process this and get back to you.`,
    `I understand you're asking about "${userMessage}". Let me provide some insights.`,
    `Regarding "${userMessage}", I've identified the following key points...`
  ];

  return responses[Math.floor(Math.random() * responses.length)];
};

const retryMessage = (message) => {
  // If it's a user message that failed to send
  if (message.role === 'user' && message.status === 'error') {
    // Update message status to sending
    message.status = 'sending';

    // Simulate sending again
    setTimeout(() => {
      message.status = 'sent';

      setTimeout(() => {
        message.status = 'delivered';

        // Trigger AI response
        setTimeout(() => {
          aiStatus.value = 'processing';

          const aiResponse = {
            id: Date.now() + 1,
            role: 'ai',
            content: '',
            timestamp: new Date(),
            status: 'loading'
          };

          messages.value.push(aiResponse);
          scrollToBottom();

          setTimeout(() => {
            aiResponse.content = generateAIResponse(message.content);
            aiResponse.status = 'completed';
            aiStatus.value = 'idle';
            scrollToBottom();
          }, 1200);
        }, 800);
      }, 500);
    }, 300);
  }
  // If it's an AI message that failed to generate
  else if (message.role === 'ai' && message.status === 'error') {
    // Find the corresponding user message
    const userMessage = messages.value.find(m => m.id === message.id - 1);
    if (userMessage) {
      // Update AI message status to loading
      message.status = 'loading';
      message.content = '';

      // Simulate response generation
      setTimeout(() => {
        message.content = generateAIResponse(userMessage.content);
        message.status = 'completed';
        aiStatus.value = 'idle';
        scrollToBottom();
      }, 1200);
    }
  }
};


</script>

<style scoped>
/* Custom scrollbar for messages container */
:deep(.messages-container) {
  &::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 99px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 99px;
    transition: all 0.3s ease;
  }

  &::-webkit-scrollbar-thumb:hover {
    background: rgba(6, 182, 212, 0.6);
    box-shadow: 0 0 10px rgba(6, 182, 212, 0.4);
  }
}

.markdown-content {
  /* white-space: pre-wrap; */
  word-break: break-word;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: bold;
}

.markdown-content :deep(p) {
  margin: 0.8em 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  padding-left: 1.5em;
  margin: 0.8em 0;
}

.markdown-content :deep(code) {
  background: #f4f4f4;
  color: #d63384;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 0.9em;
}

.markdown-content :deep(pre) {
  background: #2d2d2d;
  color: #f8f8f2;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 1em 0;
}

.markdown-content :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
  font-size: 0.95em;
}
</style>
