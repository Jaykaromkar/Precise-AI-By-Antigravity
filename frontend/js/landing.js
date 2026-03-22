const API_BASE = '/api';

if (localStorage.getItem('user_id')) {
    window.location.href = '/app';
}

const authModal = document.getElementById('authModal');
const authModalContent = document.getElementById('authModalContent');
const authForm = document.getElementById('authForm');
const authError = document.getElementById('authError');
const authSuccess = document.getElementById('authSuccess');
const authSubmitBtn = document.getElementById('authSubmitBtn');
const authTitle = document.getElementById('authTitle');
const authSubtitle = document.getElementById('authSubtitle');

const tabLogin = document.getElementById('tabLogin');
const tabRegister = document.getElementById('tabRegister');
const authTabsContainer = document.getElementById('authTabsContainer');

const emailFieldContainer = document.getElementById('emailFieldContainer');
const usernameFieldContainer = document.getElementById('usernameFieldContainer');
const passwordFieldContainer = document.getElementById('passwordFieldContainer');
const backToLoginContainer = document.getElementById('backToLoginContainer');

const emailInput = document.getElementById('email');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');

let currentMode = 'login'; // 'login' | 'register' | 'forgot'

function closeAuthModal() {
    authModalContent.classList.remove('scale-100');
    authModalContent.classList.add('scale-95');
    authModal.classList.remove('opacity-100');
    authModal.classList.add('opacity-0');
    setTimeout(() => { authModal.classList.add('hidden'); }, 300);
}

const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.target.classList.contains('hidden') === false) {
            setTimeout(() => {
                authModal.classList.remove('opacity-0', 'hidden');
                authModal.classList.add('opacity-100', 'flex');
                authModalContent.classList.remove('scale-95');
                authModalContent.classList.add('scale-100');
            }, 10);
        }
    });
});
observer.observe(authModal, { attributes: true, attributeFilter: ['class'] });

function switchTab(mode) {
    currentMode = mode;
    authError.classList.add('hidden');
    authSuccess.classList.add('hidden');
    
    if (mode === 'login') {
        authTabsContainer.classList.remove('hidden');
        authTabsContainer.classList.add('flex');
        backToLoginContainer.classList.add('hidden');
        
        emailFieldContainer.classList.add('hidden');
        emailInput.required = false;
        usernameFieldContainer.classList.remove('hidden');
        usernameInput.required = true;
        passwordFieldContainer.classList.remove('hidden');
        passwordInput.required = true;

        tabLogin.classList.add('bg-gray-800', 'text-white');
        tabLogin.classList.remove('text-gray-400');
        tabRegister.classList.remove('bg-gray-800', 'text-white');
        tabRegister.classList.add('text-gray-400', 'hover:text-gray-200');
        
        authTitle.textContent = 'Access Dashboard';
        authSubtitle.textContent = 'Enter your secure credentials to continue';
        authSubmitBtn.querySelector('span').textContent = 'Authenticate';
        
    } else if (mode === 'register') {
        authTabsContainer.classList.remove('hidden');
        authTabsContainer.classList.add('flex');
        backToLoginContainer.classList.add('hidden');

        emailFieldContainer.classList.remove('hidden');
        emailInput.required = true;
        usernameFieldContainer.classList.remove('hidden');
        usernameInput.required = true;
        passwordFieldContainer.classList.remove('hidden');
        passwordInput.required = true;

        tabRegister.classList.add('bg-gray-800', 'text-white');
        tabRegister.classList.remove('text-gray-400');
        tabLogin.classList.remove('bg-gray-800', 'text-white');
        tabLogin.classList.add('text-gray-400', 'hover:text-gray-200');
        
        authTitle.textContent = 'Create Profile';
        authSubtitle.textContent = 'Initialize your secure RAG intelligence account';
        authSubmitBtn.querySelector('span').textContent = 'Initialize Account';

    } else if (mode === 'forgot') {
        authTabsContainer.classList.add('hidden');
        authTabsContainer.classList.remove('flex');
        backToLoginContainer.classList.remove('hidden');

        emailFieldContainer.classList.remove('hidden');
        emailInput.required = true;
        usernameFieldContainer.classList.add('hidden');
        usernameInput.required = false;
        passwordFieldContainer.classList.add('hidden');
        passwordInput.required = false;

        authTitle.textContent = 'Account Recovery';
        authSubtitle.textContent = 'Receive your secure credentials via email.';
        authSubmitBtn.querySelector('span').textContent = 'Send Recovery Email';
    }
}

authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = usernameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();
    
    authError.classList.add('hidden');
    authSuccess.classList.add('hidden');
    authSubmitBtn.disabled = true;
    const originalBtnText = authSubmitBtn.innerHTML;
    authSubmitBtn.innerHTML = '<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i> Processing System...';
    lucide.createIcons();

    let endpoint = '';
    let payload = {};

    if (currentMode === 'login') {
        endpoint = '/auth/login';
        payload = { username, password };
    } else if (currentMode === 'register') {
        endpoint = '/auth/register';
        payload = { username, email, password };
    } else if (currentMode === 'forgot') {
        endpoint = '/auth/forgot-password';
        payload = { email };
    }
    
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            authSuccess.textContent = data.message;
            authSuccess.classList.remove('hidden');
            
            if (currentMode === 'login' || currentMode === 'register') {
                localStorage.setItem('user_id', data.user_id);
                localStorage.setItem('username', data.username);
                window.location.href = '/app';
            } else {
                authSubmitBtn.disabled = false;
                authSubmitBtn.innerHTML = originalBtnText;
                lucide.createIcons();
            }
        } else {
            authError.textContent = data.detail || 'System Error';
            authError.classList.remove('hidden');
            authSubmitBtn.disabled = false;
            authSubmitBtn.innerHTML = originalBtnText;
            lucide.createIcons();
        }
    } catch (err) {
        authError.textContent = 'Server connection failed';
        authError.classList.remove('hidden');
        authSubmitBtn.disabled = false;
        authSubmitBtn.innerHTML = originalBtnText;
        lucide.createIcons();
    }
});
