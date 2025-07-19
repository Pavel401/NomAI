interface ChatMessage {
    role: 'user' | 'model';
    timestamp: string;
    content: string;
    tool_calls?: Array<{
        tool_name: string;
        args: string;
        tool_call_id: string;
    }>;
    tool_returns?: Array<{
        tool_call_id: string;
        content: any;
        tool_name: string;
    }>;
    is_final?: boolean;
}

interface NutritionData {
    response: {
        foodName: string;
        portion: string;
        portionSize: number;
        confidenceScore: number;
        ingredients: Array<{
            name: string;
            calories: number;
            protein: number;
            carbs: number;
            fiber: number;
            fat: number;
            healthScore: number;
            healthComments: string;
        }>;
        primaryConcerns?: Array<{
            issue: string;
            explanation: string;
            recommendations: Array<{
                food: string;
                quantity: string;
                reasoning: string;
            }>;
        }>;
        suggestAlternatives?: Array<{
            name: string;
            calories: number;
            protein: number;
            carbs: number;
            fiber: number;
            fat: number;
            healthScore: number;
            healthComments: string;
        }>;
        overallHealthScore: number;
        overallHealthComments: string;
    };
}

class ChatApp {
    private messagesContainer: HTMLElement;
    private messageInput: HTMLTextAreaElement;
    private sendButton: HTMLButtonElement;
    private userIdInput: HTMLInputElement;
    private isTyping: boolean = false;

    constructor() {
        this.messagesContainer = document.getElementById('messages') as HTMLElement;
        this.messageInput = document.getElementById('messageInput') as HTMLTextAreaElement;
        this.sendButton = document.getElementById('sendButton') as HTMLButtonElement;
        this.userIdInput = document.getElementById('userIdInput') as HTMLInputElement;

        this.setupEventListeners();
        this.loadMessages();
    }

    private setupEventListeners(): void {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        this.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });
    }

    private autoResizeTextarea(): void {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    private async loadMessages(): Promise<void> {
        try {
            const response = await fetch('/chat/messages');
            const text = await response.text();
            
            if (text.trim()) {
                const messages = text.trim().split('\n').map(line => JSON.parse(line));
                messages.forEach(message => this.displayMessage(message));
            }
            
            this.scrollToBottom();
        } catch (error) {
            console.error('Error loading messages:', error);
            this.showError('Failed to load chat history');
        }
    }

    private async sendMessage(): Promise<void> {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        // Get user_id from input (optional)
        const userId = this.userIdInput.value.trim() || 'Pavel';

        // Get local time as ISO string
        const localTime = new Date().toISOString();

        // Display user message immediately
        const userMessage: ChatMessage = {
            role: 'user',
            timestamp: localTime,
            content: message
        };

        this.displayMessage(userMessage);
        this.messageInput.value = '';
        this.autoResizeTextarea();
        this.setTyping(true);

        try {
            const formData = new FormData();
            formData.append('prompt', message);
            formData.append('user_id', userId);
            formData.append('local_time', localTime);

            const response = await fetch('/chat/messages', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body?.getReader();
            if (!reader) {
                throw new Error('No response body');
            }

            let currentMessage: ChatMessage | null = null;
            let currentMessageElement: HTMLElement | null = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = new TextDecoder().decode(value);
                const lines = chunk.split('\n').filter(line => line.trim());

                for (const line of lines) {
                    try {
                        const messageData: ChatMessage = JSON.parse(line);
                        
                        if (messageData.is_final) {
                            // Replace the current message with the final one
                            if (currentMessageElement) {
                                currentMessageElement.remove();
                            }
                            this.displayMessage(messageData);
                        } else {
                            // Update or create streaming message
                            if (!currentMessage) {
                                currentMessage = messageData;
                                currentMessageElement = this.displayMessage(messageData);
                            } else {
                                // Update existing message content
                                currentMessage.content = messageData.content;
                                if (currentMessageElement) {
                                    this.updateMessageContent(currentMessageElement, messageData);
                                }
                            }
                        }
                    } catch (parseError) {
                        console.error('Error parsing message:', parseError);
                    }
                }
            }

        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Failed to send message. Please try again.');
        } finally {
            this.setTyping(false);
        }
    }

    private displayMessage(message: ChatMessage): HTMLElement {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role}`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Add contentDiv to messageDiv first
        messageDiv.appendChild(contentDiv);
        
        // Then update the content
        this.updateMessageContent(messageDiv, message);

        const timestamp = document.createElement('div');
        timestamp.className = 'message-timestamp';
        timestamp.textContent = this.formatTimestamp(message.timestamp);

        messageDiv.appendChild(timestamp);
        this.messagesContainer.appendChild(messageDiv);
        
        this.scrollToBottom();
        return messageDiv;
    }

    private updateMessageContent(messageElement: HTMLElement, message: ChatMessage): void {
        const contentDiv = messageElement.querySelector('.message-content') as HTMLElement;
        
        if (message.role === 'model' && message.tool_returns && message.tool_returns.length > 0) {
            // Handle nutrition data display
            const nutritionData = this.extractNutritionData(message.tool_returns);
            if (nutritionData) {
                contentDiv.innerHTML = this.formatNutritionResponse(message.content, nutritionData);
            } else {
                contentDiv.innerHTML = this.formatTextContent(message.content);
            }
        } else {
            contentDiv.innerHTML = this.formatTextContent(message.content);
        }
    }

    private extractNutritionData(toolReturns: any[]): NutritionData | null {
        console.log('Extracting nutrition data from:', toolReturns);
        for (const toolReturn of toolReturns) {
            console.log('Checking tool return:', toolReturn.tool_name, 'has content:', !!toolReturn.content);
            if (toolReturn.tool_name === 'calculate_nutrition_by_food_description' && toolReturn.content) {
                console.log('Found nutrition data:', toolReturn.content);
                return toolReturn.content as NutritionData;
            }
        }
        console.log('No nutrition data found');
        return null;
    }

    private formatNutritionResponse(content: string, nutritionData: NutritionData): string {
        let html = '';
        
        if (content) {
            html += `<div>${this.formatTextContent(content)}</div>`;
        }

        const data = nutritionData.response;
        
        html += `<div class="nutrition-info">`;
        
        // Food name and basic info
        html += `<div class="nutrition-section">`;
        html += `<h4>📊 ${data.foodName}</h4>`;
        html += `<p><strong>Portion:</strong> ${data.portionSize} ${data.portion}</p>`;
        html += `<p><strong>Confidence Score:</strong> ${data.confidenceScore}/10</p>`;
        html += `</div>`;

        // Overall nutrition
        if (data.ingredients && data.ingredients.length > 0) {
            const totalNutrition = this.calculateTotalNutrition(data.ingredients);
            
            html += `<div class="nutrition-section">`;
            html += `<h4>🥗 Total Nutrition</h4>`;
            html += `<div class="nutrition-item">`;
            html += `<strong>Calories:</strong> ${totalNutrition.calories} | `;
            html += `<strong>Protein:</strong> ${totalNutrition.protein}g | `;
            html += `<strong>Carbs:</strong> ${totalNutrition.carbs}g | `;
            html += `<strong>Fiber:</strong> ${totalNutrition.fiber}g | `;
            html += `<strong>Fat:</strong> ${totalNutrition.fat}g`;
            html += `</div>`;
            html += `</div>`;

            // Individual ingredients
            if (data.ingredients.length > 1) {
                html += `<div class="nutrition-section">`;
                html += `<h4>🔍 Breakdown by Ingredient</h4>`;
                data.ingredients.forEach(ingredient => {
                    const healthScoreClass = ingredient.healthScore >= 7 ? '' : ingredient.healthScore >= 5 ? 'medium' : 'low';
                    html += `<div class="nutrition-item">`;
                    html += `<strong>${ingredient.name}</strong> `;
                    html += `<span class="health-score ${healthScoreClass}">Health Score: ${ingredient.healthScore}/10</span><br>`;
                    html += `Calories: ${ingredient.calories} | Protein: ${ingredient.protein}g | Carbs: ${ingredient.carbs}g | Fat: ${ingredient.fat}g<br>`;
                    html += `<small>${ingredient.healthComments}</small>`;
                    html += `</div>`;
                });
                html += `</div>`;
            }
        }

        // Health score
        const overallScoreClass = data.overallHealthScore >= 7 ? '' : data.overallHealthScore >= 5 ? 'medium' : 'low';
        html += `<div class="nutrition-section">`;
        html += `<h4>💡 Overall Health Assessment</h4>`;
        html += `<div class="nutrition-item">`;
        html += `<span class="health-score ${overallScoreClass}">Overall Score: ${data.overallHealthScore}/10</span><br>`;
        html += `<small>${data.overallHealthComments}</small>`;
        html += `</div>`;
        html += `</div>`;

        // Primary concerns
        if (data.primaryConcerns && data.primaryConcerns.length > 0) {
            html += `<div class="nutrition-section">`;
            html += `<h4>⚠️ Health Concerns</h4>`;
            data.primaryConcerns.forEach(concern => {
                html += `<div class="nutrition-item">`;
                html += `<strong>${concern.issue}</strong><br>`;
                html += `<small>${concern.explanation}</small>`;
                if (concern.recommendations && concern.recommendations.length > 0) {
                    html += `<br><strong>Recommendations:</strong><br>`;
                    concern.recommendations.forEach(rec => {
                        html += `<small>• ${rec.food} (${rec.quantity}): ${rec.reasoning}</small><br>`;
                    });
                }
                html += `</div>`;
            });
            html += `</div>`;
        }

        // Alternatives
        if (data.suggestAlternatives && data.suggestAlternatives.length > 0) {
            html += `<div class="nutrition-section">`;
            html += `<h4>🔄 Healthier Alternatives</h4>`;
            data.suggestAlternatives.forEach(alt => {
                const altScoreClass = alt.healthScore >= 7 ? '' : alt.healthScore >= 5 ? 'medium' : 'low';
                html += `<div class="nutrition-item">`;
                html += `<strong>${alt.name}</strong> `;
                html += `<span class="health-score ${altScoreClass}">${alt.healthScore}/10</span><br>`;
                html += `Calories: ${alt.calories} | Protein: ${alt.protein}g | Carbs: ${alt.carbs}g | Fat: ${alt.fat}g<br>`;
                html += `<small>${alt.healthComments}</small>`;
                html += `</div>`;
            });
            html += `</div>`;
        }

        html += `</div>`;
        return html;
    }

    private calculateTotalNutrition(ingredients: any[]) {
        return ingredients.reduce((total, ingredient) => ({
            calories: total.calories + ingredient.calories,
            protein: total.protein + ingredient.protein,
            carbs: total.carbs + ingredient.carbs,
            fiber: total.fiber + ingredient.fiber,
            fat: total.fat + ingredient.fat
        }), { calories: 0, protein: 0, carbs: 0, fiber: 0, fat: 0 });
    }

    private formatTextContent(content: string): string {
        // Convert newlines to <br> tags and preserve formatting
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    private formatTimestamp(timestamp: string): string {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
        });
    }

    private setTyping(typing: boolean): void {
        this.isTyping = typing;
        this.sendButton.disabled = typing;
        
        const existingIndicator = document.querySelector('.typing-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }

        if (typing) {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'typing-indicator';
            typingDiv.innerHTML = `
                AI is thinking
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            `;
            this.messagesContainer.appendChild(typingDiv);
            this.scrollToBottom();
        }
    }

    private showError(message: string): void {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        this.messagesContainer.appendChild(errorDiv);
        this.scrollToBottom();

        // Remove error after 5 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }

    private scrollToBottom(): void {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
}

function initChatApp() {
    new ChatApp();
}
