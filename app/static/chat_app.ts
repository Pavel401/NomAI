// BIG FAT WARNING: to avoid the complexity of npm, this typescript is compiled in the browser
// there's currently no static type checking

import { marked } from 'https://cdnjs.cloudflare.com/ajax/libs/marked/15.0.0/lib/marked.esm.js'
const convElement = document.getElementById('conversation')

const promptInput = document.getElementById('prompt-input') as HTMLInputElement
const spinner = document.getElementById('spinner')

// stream the response and render messages as each chunk is received
// data is sent as newline-delimited JSON
async function onFetchResponse(response: Response): Promise<void> {
    let text = ''
    let decoder = new TextDecoder()
    if (response.ok) {
        const reader = response.body?.getReader()
        if (reader) {
            while (true) {
                const { done, value } = await reader.read()
                if (done) {
                    break
                }
                text += decoder.decode(value)
                addMessages(text)
                spinner?.classList.remove('active')
            }
        }
        addMessages(text)
        if (promptInput) {
            promptInput.disabled = false
            promptInput.focus()
        }
    } else {
        const text = await response.text()
        console.error(`Unexpected response: ${response.status}`, { response, text })
        throw new Error(`Unexpected response: ${response.status}`)
    }
}

// The format of messages, this matches pydantic-ai both for brevity and understanding
// in production, you might not want to keep this format all the way to the frontend
interface Message {
    role: string
    content: string
    timestamp: string
}

function showDebug(message: string) {
    const debug = document.getElementById('debug');
    if (debug) {
        debug.textContent += message + '\n';
        debug.classList.remove('d-none');
    }
}

// take raw response text and render messages into the `#conversation` element
// Message timestamp is assumed to be a unique identifier of a message, and is used to deduplicate
// hence you can send data about the same message multiple times, and it will be updated
// instead of creating a new message elements
function addMessages(responseText: string) {
    try {
        showDebug("Raw responseText:\n" + responseText);
        const lines = responseText.split('\n')
        const messages: Message[] = lines.filter(line => line.length > 1).map(j => JSON.parse(j))
        
        // Hide empty state when messages are present
        const emptyState = document.querySelector('.empty-state') as HTMLElement
        if (messages.length > 0 && emptyState) {
            emptyState.style.display = 'none'
        }
        
        for (const message of messages) {
            const { timestamp, role, content } = message
            const id = `msg-${timestamp}`
            let msgDiv = document.getElementById(id)
            if (!msgDiv) {
                msgDiv = document.createElement('div')
                msgDiv.id = id
                msgDiv.title = `${role} at ${timestamp}`
                msgDiv.classList.add('message', role)
                
                // Create message wrapper with avatar
                const messageWrapper = document.createElement('div')
                messageWrapper.className = `d-flex ${role === 'user' ? 'justify-content-end' : 'justify-content-start'} align-items-start`
                
                if (role !== 'user') {
                    const avatar = document.createElement('div')
                    avatar.className = 'avatar ai-avatar'
                    avatar.innerHTML = '<i class="fas fa-robot"></i>'
                    messageWrapper.appendChild(avatar)
                }
                
                const messageContent = document.createElement('div')
                messageContent.className = 'message-content'
                messageWrapper.appendChild(messageContent)
                
                if (role === 'user') {
                    const avatar = document.createElement('div')
                    avatar.className = 'avatar user-avatar ms-2'
                    avatar.innerHTML = '<i class="fas fa-user"></i>'
                    messageWrapper.appendChild(avatar)
                }
                
                msgDiv.appendChild(messageWrapper)
                if (convElement) {
                    convElement.appendChild(msgDiv)
                }
            }
            
            const messageContent = msgDiv.querySelector('.message-content') as HTMLElement
            if (messageContent) {
                messageContent.innerHTML = marked.parse(content)
            }
        }
        // Scroll to bottom of conversation
        if (convElement) {
            convElement.scrollTo({ top: convElement.scrollHeight, behavior: 'smooth' })
        }
    } catch (err) {
        console.error("Error parsing or rendering messages:", err, responseText)
        const errorElement = document.getElementById('error')
        if (errorElement) {
            errorElement.textContent = "Error parsing messages. See console for details."
            errorElement.classList.remove('d-none')
        }
        showDebug("Error parsing messages: " + err);
    }
}

function onError(error: any) {
    console.error(error)
    const errorElement = document.getElementById('error')
    const spinnerElement = document.getElementById('spinner')
    
    if (errorElement) {
        errorElement.classList.remove('d-none')
    }
    if (spinnerElement) {
        spinnerElement.classList.remove('active')
    }
}

async function onSubmit(e: SubmitEvent): Promise<void> {
    e.preventDefault()
    
    const sendBtn = document.querySelector('.send-btn') as HTMLButtonElement
    const form = e.target as HTMLFormElement
    
    // Show loading state
    spinner?.classList.add('active')
    if (sendBtn) {
        sendBtn.disabled = true
        sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...'
    }
    
    const body = new FormData(form)
    const userMessage = body.get('prompt') as string

    // Add user message immediately to the UI
    if (userMessage.trim()) {
        const userMsg = {
            role: 'user',
            content: userMessage,
            timestamp: Date.now().toString()
        }
        addMessages(JSON.stringify(userMsg))
    }

    if (promptInput) {
        promptInput.value = ''
        promptInput.disabled = true
    }

    try {
        showDebug("Submitting prompt: " + body.get('prompt'));
        const response = await fetch('/chat/messages', { method: 'POST', body })
        await onFetchResponse(response)
    } catch (err) {
        onError(err)
    } finally {
        // Reset button state
        if (sendBtn) {
            sendBtn.disabled = false
            sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send'
        }
        if (promptInput) {
            promptInput.disabled = false
            promptInput.focus()
        }
    }
}

// call onSubmit when the form is submitted (e.g. user clicks the send button or hits Enter)
document.querySelector('form')?.addEventListener('submit', (e) => onSubmit(e).catch(onError))

// load messages on page load
fetch('/chat/messages').then(onFetchResponse).catch(onError)

// Add keyboard shortcut for sending message (Ctrl+Enter or Cmd+Enter)
if (promptInput) {
    promptInput.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault()
            const form = document.querySelector('form') as HTMLFormElement
            if (form && promptInput.value.trim()) {
                form.dispatchEvent(new Event('submit'))
            }
        }
    })

    // Auto-resize textarea behavior for input
    promptInput.addEventListener('input', () => {
        if (promptInput.value.length > 100) {
            promptInput.style.height = 'auto'
            promptInput.style.height = Math.min(promptInput.scrollHeight, 120) + 'px'
        } else {
            promptInput.style.height = 'auto'
        }
    })
}

// Helper function for suggestion chips (defined globally for onclick)
;(window as any).fillPrompt = function(text: string) {
    if (promptInput) {
        promptInput.value = text
        promptInput.focus()
        // Trigger input event to handle auto-resize
        promptInput.dispatchEvent(new Event('input'))
    }
}
