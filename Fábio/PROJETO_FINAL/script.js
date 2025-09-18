// Funções para o Modal de Mensagem Padronizado (Escopo Global)
function showMessageModal(title, message, type = '') {
    const modal = document.getElementById('messageModal');
    if (!modal) return;
    const modalTitle = document.getElementById('messageModalTitle');
    const modalText = document.getElementById('messageModalText');
    const modalHeader = modal.querySelector('.modal-header');
    modalTitle.textContent = title;
    modalText.innerHTML = message.replace(/\n/g, '<br>');
    modalHeader.classList.remove('success', 'error', 'warning', 'info');
    if (type) modalHeader.classList.add(type);
    modal.classList.remove('hidden');
}

function closeMessageModal() {
    const modal = document.getElementById('messageModal');
    if (modal) modal.classList.add('hidden');
}

// Funções para o Modal de Confirmação
function showConfirmModal(title, message, onConfirm) {
    const modal = document.getElementById('confirmModal');
    if (!modal) return;
    document.getElementById('confirmModalTitle').textContent = title;
    document.getElementById('confirmModalText').textContent = message;
    const confirmBtn = document.getElementById('confirmOkBtn');
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    newConfirmBtn.addEventListener('click', () => {
        onConfirm();
        closeConfirmModal();
    });
    modal.classList.remove('hidden');
}

function closeConfirmModal() {
    const modal = document.getElementById('confirmModal');
    if (modal) modal.classList.add('hidden');
}

// --- INÍCIO DO CÓDIGO DE ANIMAÇÃO DE PÁGINA ---

const pageOrder = [
    // Páginas do Aluno
    'dashboard.html',
    'materials.html',
    // Páginas do Professor
    'teacher-dashboard.html',
    'admin.html',
    'database.html',
    'teacher-diary.html',
    'teacher-materials.html',
    // Páginas de Informações
    'horario-onibus.html',
    'calendario-aulas.html',
    'endereco-aula.html',
    'contato.html'
];

function handlePageTransition() {
    const content = document.querySelector('.content');
    if (!content) return;

    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const previousPageIndexStr = sessionStorage.getItem('currentPageIndex');
    const currentPageIndex = pageOrder.indexOf(currentPage);

    content.classList.remove('slide-in-from-right', 'slide-in-from-left');

    const applyAnimation = () => {
        if (currentPageIndex === -1) {
            sessionStorage.setItem('currentPageIndex', null);
            return;
        }

        if (previousPageIndexStr && previousPageIndexStr !== 'null') {
            const prevIndex = parseInt(previousPageIndexStr, 10);
            if (currentPageIndex > prevIndex) {
                content.classList.add('slide-in-from-right');
            } else if (currentPageIndex < prevIndex) {
                content.classList.add('slide-in-from-left');
            }
        }
        
        sessionStorage.setItem('currentPageIndex', currentPageIndex);
    };

    requestAnimationFrame(applyAnimation);
}

// --- FIM DO CÓDIGO DE ANIMAÇÃO DE PÁGINA ---

// Lógica principal que executa após o carregamento da página
document.addEventListener("DOMContentLoaded", () => {
    // A chamada para a função de animação deve estar aqui
    handlePageTransition();
    
    const loginForm = document.getElementById("loginForm");

    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = document.getElementById("username").value;
            const password = document.getElementById("password").value;
            try {
                const response = await fetch('http://127.0.0.1:5000/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password }),
                });
                const data = await response.json();
                if (data.success) {
                    localStorage.setItem("isLoggedIn", "true");
                    localStorage.setItem("userId", data.user.id);
                    localStorage.setItem("username", data.user.username);
                    localStorage.setItem("userRole", data.user.role);
                    localStorage.setItem("userName", data.user.full_name);
                    localStorage.setItem("userStudentId", data.user.student_id);
                    window.location.href = data.user.role === "teacher" ? "teacher-dashboard.html" : "dashboard.html";
                } else {
                    showMessageModal('Erro no Login', data.message || 'Erro desconhecido.', 'error');
                }
            } catch (error) {
                console.error('Erro de rede ou servidor ao tentar logar:', error);
                showMessageModal('Erro de Conexão', 'Não foi possível conectar ao servidor. Tente novamente mais tarde.', 'error');
            }
        });
    }

    const isLoginPage = window.location.pathname.endsWith("index.html") || window.location.pathname === "/";
    if (!isLoginPage && !localStorage.getItem("isLoggedIn")) {
        window.location.href = "index.html";
    }

    const userRole = localStorage.getItem("userRole");
    if (localStorage.getItem("isLoggedIn") === 'true') {
        const currentPage = window.location.pathname.split('/').pop();
        const strictTeacherPages = ['teacher-dashboard.html', 'admin.html', 'database.html', 'teacher-diary.html', 'teacher-materials.html'];
        const strictStudentPages = ['dashboard.html'];
        if (userRole === 'teacher' && strictStudentPages.includes(currentPage)) {
            window.location.href = "teacher-dashboard.html";
        } else if (userRole === 'student' && strictTeacherPages.includes(currentPage)) {
            window.location.href = "dashboard.html";
        }
    }

    const navElements = {
        'teacher': { 'navAdmin': 'list-item', 'navBancoDados': 'list-item', 'navDiarioClasseProf': 'list-item', 'navMateriaisProf': 'list-item', 'navDiarioClasseAluno': 'none', 'navMateriaisAluno': 'none' },
        'student': { 'navAdmin': 'none', 'navBancoDados': 'none', 'navDiarioClasseProf': 'none', 'navMateriaisProf': 'none', 'navDiarioClasseAluno': 'list-item', 'navMateriaisAluno': 'list-item' }
    };
    if (navElements[userRole]) {
        for (const [id, display] of Object.entries(navElements[userRole])) {
            const elem = document.getElementById(id);
            if (elem) elem.style.display = display;
        }
    }

    async function logout() {
        const userId = localStorage.getItem("userId");
        if (userId) {
            try {
                await fetch(`http://127.0.0.1:5000/logout/${userId}`, { method: 'POST' });
            } catch (error) {
                console.error('Erro ao atualizar status de logout:', error);
            }
        }
        localStorage.clear();
        window.location.href = "index.html";
    }

    const userAvatar = document.querySelector(".user-avatar");
    if (userAvatar) {
        userAvatar.addEventListener("click", () => {
            showConfirmModal("Confirmar Logout", "Deseja realmente sair do sistema?", logout);
        });
        userAvatar.style.cursor = "pointer";
        userAvatar.title = "Clique para fazer logout";
    }

    if (window.location.pathname.endsWith('database.html')) {
        window.fetchAlunosFromBackend();
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal').forEach(modal => modal.classList.add('hidden'));
        }
    });

    const addAlunoForm = document.getElementById('addAlunoForm');
    if (addAlunoForm) {
        addAlunoForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const formData = new FormData(addAlunoForm);
            const alunoData = Object.fromEntries(formData.entries());
            sendAlunoToBackend(alunoData);
        });
    }

    const editAlunoForm = document.getElementById('editAlunoForm');
    if (editAlunoForm) {
        editAlunoForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const formData = new FormData(editAlunoForm);
            const alunoData = Object.fromEntries(formData.entries());
            const alunoId = alunoData.id;
            delete alunoData.id;
            sendEditedAlunoToBackend(alunoId, alunoData);
        });
    }
});

// =====================================================================================
// FUNÇÕES GLOBAIS
// =====================================================================================

window.abrirWhatsApp = function() {
    window.open("https://chat.whatsapp.com/GHZuEpQhb5uGFROPWioy9o?mode=ac_c", '_blank');
}

let currentPage = 1;
const rowsPerPage = 20; // Define quantos alunos serão exibidos por página

window.fetchAlunosFromBackend = async function(page = 1) {
    currentPage = page;
    try {
        const response = await fetch(`http://127.0.0.1:5000/alunos?page=${page}&limit=${rowsPerPage}`);
        if (!response.ok) throw new Error(`Erro HTTP! Status: ${response.status}`);

        const data = await response.json();
        const alunos = data.alunos;
        const totalAlunos = data.total;

        displayAlunosInInfoTable(alunos); 
        setupPagination(totalAlunos, page);

    } catch (error) {
        console.error('Erro ao buscar alunos:', error);
        const tbody = document.querySelector('#table_info_alunos tbody');
        if (tbody) tbody.innerHTML = `<tr><td colspan="12" style="text-align: center; color: red;">Erro ao carregar dados dos alunos.</td></tr>`;
    }
};

function setupPagination(totalItems, currentPage) {
    const paginationControls = document.getElementById('paginationControls');
    if (!paginationControls) return;
    paginationControls.innerHTML = '';

    const totalPages = Math.ceil(totalItems / rowsPerPage);

    const prevBtn = document.createElement('button');
    prevBtn.textContent = '« Anterior';
    prevBtn.className = 'action-btn small';
    prevBtn.disabled = currentPage === 1;
    prevBtn.onclick = () => window.fetchAlunosFromBackend(currentPage - 1);
    paginationControls.appendChild(prevBtn);

    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, currentPage + 2);

    if (startPage > 1) {
        paginationControls.appendChild(document.createTextNode('...'));
    }

    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = 'action-btn small';
        if (i === currentPage) {
            pageBtn.classList.add('active'); 
        }
        pageBtn.onclick = () => window.fetchAlunosFromBackend(i);
        paginationControls.appendChild(pageBtn);
    }

    if (endPage < totalPages) {
        paginationControls.appendChild(document.createTextNode('...'));
    }

    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'Próxima »';
    nextBtn.className = 'action-btn small';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.onclick = () => window.fetchAlunosFromBackend(currentPage + 1);
    paginationControls.appendChild(nextBtn);
}

function displayAlunosInInfoTable(alunos) {
    const tbody = document.querySelector('#table_info_alunos tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (alunos.length === 0) {
        tbody.innerHTML = `<tr><td colspan="12" style="text-align: center;">Nenhum aluno encontrado.</td></tr>`;
        return;
    }
    alunos.forEach(aluno => {
        const row = document.createElement('tr');
        row.innerHTML = `<td>${aluno.turma || ''}</td><td>${aluno.nome || ''}</td><td>${aluno.email || ''}</td><td>${aluno.telefone || ''}</td><td>${aluno.data_nascimento || ''}</td><td>${aluno.rg || ''}</td><td>${aluno.cpf || ''}</td><td>${aluno.endereco || ''}</td><td>${aluno.escolaridade || ''}</td><td>${aluno.escola || ''}</td><td>${aluno.responsavel || ''}</td><td><button class="action-btn small" onclick="editAluno(${aluno.id})" title="Editar">✏️</button><button class="action-btn small danger" onclick="deleteAluno(${aluno.id})" title="Excluir">🗑️</button></td>`;
        tbody.appendChild(row);
    });
};

async function sendAlunoToBackend(alunoData) {
    if (!validateAlunoForm(alunoData, false)) return;
    try {
        const response = await fetch('http://127.0.0.1:5000/alunos/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(alunoData),
        });
        const data = await response.json();
        if (data.success) {
            let successMessage = 'Aluno adicionado com sucesso!';
            if (data.generated_username && data.generated_password) {
                successMessage += `\n\nCredenciais de Login:\nUsuário: ${data.generated_username}\nSenha: ${data.generated_password}`;
            }
            showMessageModal('Sucesso!', successMessage, 'success');
            closeAddAlunoModal();
            await window.fetchAlunosFromBackend(); 
        } else {
            showMessageModal('Erro', 'Erro ao adicionar aluno: ' + (data.message || 'Erro desconhecido.'), 'error');
        }
    } catch (error) {
        showMessageModal('Erro de Conexão', 'Não foi possível conectar ao servidor. Tente novamente mais tarde.', 'error');
    }
}

window.deleteAluno = async function(alunoId) {
    showConfirmModal('Confirmar Exclusão', `Tem certeza que deseja excluir o aluno com ID ${alunoId}? Esta ação não pode ser desfeita.`, async () => {
        try {
            const response = await fetch(`http://127.0.0.1:5000/alunos/delete/${alunoId}`, { method: 'DELETE' });
            const data = await response.json();
            if (data.success) {
                showMessageModal('Sucesso!', 'Aluno excluído com sucesso!', 'success');
                await window.fetchAlunosFromBackend();
            } else {
                showMessageModal('Erro', 'Erro ao excluir aluno: ' + (data.message || 'Erro desconhecido.'), 'error');
            }
        } catch (error) {
            showMessageModal('Erro de Conexão', 'Não foi possível conectar ao servidor para excluir o aluno.', 'error');
        }
    });
};

// =====================================================================================
// Funções que você resumiu, adicione o código completo se necessário
// =====================================================================================

window.fetchStudentOverallStatusFromBackend = async function() {};
function displayStudentOverallStatusTable(statuses) {};
window.fetchLoginAlunosFromBackend = async function() {};
function displayLoginAlunosTable(users) {};
window.fetchAtividadesAlunosFromBackend = async function() {};
function displayAtividadesAlunosTable(atividades) {};
function validateAlunoForm(alunoData, isEdit = false) { return true; };
window.editAluno = async function(alunoId) {};
async function sendEditedAlunoToBackend(alunoId, alunoData) {};
window.changeTable = function() {};
window.searchTable = function() {};
window.addRecord = function() {};
window.editRecord = function() {};
window.closeAddAlunoModal = () => {
    document.getElementById('addAlunoModal').classList.add('hidden');
    document.getElementById('addAlunoForm').reset();
};
window.closeEditAlunoModal = () => {
    document.getElementById('editAlunoModal').classList.add('hidden');
    document.getElementById('editAlunoForm').reset();
};