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

// Lógica principal que executa após o carregamento da página
document.addEventListener("DOMContentLoaded", () => {
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
        const strictStudentPages = ['dashboard.html', 'materials.html'];
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
        window.fetchAlunosFromBackend(1); // Carrega a primeira página por defeito
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

    // =====================================================================================
    // LÓGICA PARA O MURAL DE AVISOS (TEACHER DASHBOARD)
    // =====================================================================================

    if (window.location.pathname.endsWith('teacher-dashboard.html')) {
        
        const addAvisoForm = document.getElementById('addAvisoForm');
        const avisosList = document.getElementById('avisosList');

        async function loadAvisos() {
            if (!avisosList) return;
            avisosList.innerHTML = '<p>A carregar avisos...</p>';

            try {
                const response = await fetch('http://127.0.0.1:5000/avisos');
                const avisos = await response.json();

                avisosList.innerHTML = '';
                if (avisos.length === 0) {
                    avisosList.innerHTML = '<p>Nenhum aviso publicado ainda.</p>';
                    return;
                }

                avisos.forEach(aviso => {
                    const dataAviso = new Date(aviso.data_criacao).toLocaleString('pt-BR');
                    const avisoItem = document.createElement('div');
                    avisoItem.className = 'aviso-item';
                    avisoItem.innerHTML = `
                        <div class="aviso-content">
                            <div class="aviso-header">
                                <h4>${aviso.titulo}</h4>
                                <div class="aviso-actions">
                                    <button class="action-btn small danger" onclick="deleteAviso(${aviso.id})">Apagar</button>
                                </div>
                            </div>
                            <p class="aviso-corpo">${aviso.mensagem}</p>
                            <div class="aviso-meta">
                                <span>Publicado por: <strong>${aviso.autor || 'Professor'}</strong> em ${dataAviso}</span>
                            </div>
                        </div>
                    `;
                    avisosList.appendChild(avisoItem);
                });
            } catch (error) {
                console.error('Erro ao carregar avisos:', error);
                avisosList.innerHTML = '<p style="color: red;">Não foi possível carregar os avisos.</p>';
            }
        }

        window.deleteAviso = async function(avisoId) {
            showConfirmModal('Confirmar Exclusão', 'Tem a certeza de que deseja apagar este aviso?', async () => {
                try {
                    const response = await fetch(`http://127.0.0.1:5000/avisos/delete/${avisoId}`, {
                        method: 'DELETE'
                    });
                    const data = await response.json();
                    if (data.success) {
                        showMessageModal('Sucesso!', 'Aviso apagado com sucesso.', 'success');
                        loadAvisos();
                    } else {
                        throw new Error(data.message);
                    }
                } catch (error) {
                    console.error('Erro ao apagar aviso:', error);
                    showMessageModal('Erro!', 'Não foi possível apagar o aviso.', 'error');
                }
            });
        }

        if (addAvisoForm) {
            addAvisoForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const titulo = document.getElementById('avisoTitulo').value;
                const mensagem = document.getElementById('avisoMensagem').value;
                const userId = localStorage.getItem('userId');

                if (!titulo || !mensagem) {
                    showMessageModal('Atenção', 'Título e mensagem são obrigatórios.', 'warning');
                    return;
                }

                try {
                    const response = await fetch('http://127.0.0.1:5000/avisos/add', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ titulo, mensagem, user_id: userId })
                    });
                    const data = await response.json();
                    if (data.success) {
                        showMessageModal('Sucesso!', 'Aviso publicado com sucesso!', 'success');
                        addAvisoForm.reset();
                        loadAvisos();
                    } else {
                        throw new Error(data.message);
                    }
                } catch (error) {
                    console.error('Erro ao adicionar aviso:', error);
                    showMessageModal('Erro!', 'Não foi possível publicar o aviso.', 'error');
                }
            });
        }

        loadAvisos();
    }

    // =====================================================================================
    // LÓGICA PARA O MURAL DE AVISOS (STUDENT DASHBOARD)
    // =====================================================================================

    if (window.location.pathname.endsWith('dashboard.html')) {
        const studentAvisosList = document.getElementById('studentAvisosList');

        async function loadStudentAvisos() {
            if (!studentAvisosList) return;
            studentAvisosList.innerHTML = '<p>A carregar avisos...</p>';

            try {
                const response = await fetch('http://127.0.0.1:5000/avisos');
                const avisos = await response.json();

                studentAvisosList.innerHTML = '';
                if (avisos.length === 0) {
                    studentAvisosList.innerHTML = '<p>Nenhum aviso publicado pelo professor.</p>';
                    return;
                }

                avisos.forEach(aviso => {
                    const dataAviso = new Date(aviso.data_criacao).toLocaleString('pt-BR');
                    const avisoItem = document.createElement('div');
                    avisoItem.className = 'aviso-item';
                    avisoItem.innerHTML = `
                        <div class="aviso-content">
                            <div class="aviso-header">
                                <h4>${aviso.titulo}</h4>
                            </div>
                            <p class="aviso-corpo">${aviso.mensagem}</p>
                            <div class="aviso-meta">
                                <span>Publicado por: <strong>${aviso.autor || 'Professor'}</strong> em ${dataAviso}</span>
                            </div>
                        </div>
                    `;
                    studentAvisosList.appendChild(avisoItem);
                });
            } catch (error) {
                console.error('Erro ao carregar avisos:', error);
                studentAvisosList.innerHTML = '<p style="color: red;">Não foi possível carregar os avisos.</p>';
            }
        }
        
        loadStudentAvisos();
    }
});

// =====================================================================================
// FUNÇÕES GLOBAIS
// =====================================================================================

window.abrirWhatsApp = function() {
    window.open("https://chat.whatsapp.com/GHZuEpQhb5uGFROPWioy9o?mode=ac_c", '_blank');
}

// FUNÇÕES DE CRUD DE ALUNOS E TABELA PRINCIPAL
let currentPage = 1;
const rowsPerPage = 20;

window.fetchAlunosFromBackend = async function(page = 1, searchTerm = "") {
    currentPage = page;
    try {
        const response = await fetch(`http://127.0.0.1:5000/alunos?page=${page}&limit=${rowsPerPage}&search=${searchTerm}`);
        if (!response.ok) throw new Error(`Erro HTTP! Status: ${response.status}`);
        
        const data = await response.json();
        const alunos = data.alunos;
        const totalAlunos = data.total;

        displayAlunosInInfoTable(alunos); 
        setupPagination(totalAlunos, page, searchTerm);

    } catch (error) {
        console.error('Erro ao buscar alunos:', error);
        const tbody = document.querySelector('#table_info_alunos tbody');
        if (tbody) tbody.innerHTML = `<tr><td colspan="12" style="text-align: center; color: red;">Erro ao carregar dados dos alunos.</td></tr>`;
    }
};

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

function setupPagination(totalItems, currentPage, searchTerm = "") {
    const paginationControls = document.getElementById('paginationControls');
    if (!paginationControls) return;
    paginationControls.innerHTML = '';
    
    const totalPages = Math.ceil(totalItems / rowsPerPage);

    const prevBtn = document.createElement('button');
    prevBtn.textContent = '« Anterior';
    prevBtn.className = 'action-btn small';
    prevBtn.disabled = currentPage === 1;
    prevBtn.onclick = () => window.fetchAlunosFromBackend(currentPage - 1, searchTerm);
    paginationControls.appendChild(prevBtn);

    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, currentPage + 2);

    if (startPage > 1) { paginationControls.appendChild(document.createTextNode('...')); }
    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        pageBtn.className = 'action-btn small';
        if (i === currentPage) { pageBtn.classList.add('active'); }
        pageBtn.onclick = () => window.fetchAlunosFromBackend(i, searchTerm);
        paginationControls.appendChild(pageBtn);
    }
    if (endPage < totalPages) { paginationControls.appendChild(document.createTextNode('...')); }
    
    const nextBtn = document.createElement('button');
    nextBtn.textContent = 'Próxima »';
    nextBtn.className = 'action-btn small';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.onclick = () => window.fetchAlunosFromBackend(currentPage + 1, searchTerm);
    paginationControls.appendChild(nextBtn);
}

function validateAlunoForm(alunoData, isEdit = false) { return true; };

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
            await window.fetchAlunosFromBackend(currentPage); 
        } else {
            showMessageModal('Erro', 'Erro ao adicionar aluno: ' + (data.message || 'Erro desconhecido.'), 'error');
        }
    } catch (error) {
        showMessageModal('Erro de Conexão', 'Não foi possível conectar ao servidor. Tente novamente mais tarde.', 'error');
    }
}

window.editAluno = async function(alunoId) {
    try {
        const response = await fetch(`http://127.0.0.1:5000/alunos/${alunoId}`);
        if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
        const aluno = await response.json();

        document.getElementById('editAlunoId').value = aluno.id;
        document.getElementById('editTurma').value = aluno.turma;
        document.getElementById('editNome').value = aluno.nome;
        document.getElementById('editEmail').value = aluno.email;
        document.getElementById('editTelefone').value = aluno.telefone;
        document.getElementById('editDataNascimento').value = aluno.data_nascimento;
        document.getElementById('editRg').value = aluno.rg;
        document.getElementById('editCpf').value = aluno.cpf;
        document.getElementById('editEndereco').value = aluno.endereco;
        document.getElementById('editEscolaridade').value = aluno.escolaridade;
        document.getElementById('editEscola').value = aluno.escola;
        document.getElementById('editResponsavel').value = aluno.responsavel;

        document.getElementById('editAlunoModal').classList.remove('hidden');
    } catch (error) {
        console.error('Erro ao buscar dados do aluno para edição:', error);
        showMessageModal('Erro', 'Não foi possível carregar os dados do aluno para edição.', 'error');
    }
};

async function sendEditedAlunoToBackend(alunoId, alunoData) {
    if (!validateAlunoForm(alunoData, true)) return;
    try {
        const response = await fetch(`http://127.0.0.1:5000/alunos/edit/${alunoId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(alunoData),
        });
        const data = await response.json();
        if (data.success) {
            showMessageModal('Sucesso!', 'Aluno atualizado com sucesso!', 'success');
            closeEditAlunoModal();
            await window.fetchAlunosFromBackend(currentPage);
        } else {
            showMessageModal('Erro', 'Erro ao atualizar aluno: ' + (data.message || 'Erro desconhecido.'), 'error');
        }
    } catch (error) {
        showMessageModal('Erro de Conexão', 'Não foi possível conectar ao servidor para editar o aluno.', 'error');
    }
}

window.deleteAluno = async function(alunoId) {
    showConfirmModal('Confirmar Exclusão', `Tem certeza que deseja excluir o aluno com ID ${alunoId}? O seu utilizador de login também será apagado. Esta ação não pode ser desfeita.`, async () => {
        try {
            const response = await fetch(`http://127.0.0.1:5000/alunos/delete/${alunoId}`, { method: 'DELETE' });
            const data = await response.json();
            if (data.success) {
                showMessageModal('Sucesso!', 'Aluno e utilizador de login excluídos com sucesso!', 'success');
                await window.fetchAlunosFromBackend(currentPage);
            } else {
                showMessageModal('Erro', 'Erro ao excluir aluno: ' + (data.message || 'Erro desconhecido.'), 'error');
            }
        } catch (error) {
            showMessageModal('Erro de Conexão', 'Não foi possível conectar ao servidor para excluir o aluno.', 'error');
        }
    });
};

// =====================================================================================
// FUNÇÕES DA PÁGINA DE BANCO DE DADOS (adição de 18/09/2025)
// =====================================================================================

window.changeTable = function() {
    document.getElementById('table_info_alunos').classList.add('hidden');
    document.getElementById('table_status_alunos').classList.add('hidden');
    document.getElementById('table_login_alunos').classList.add('hidden');

    const selectedValue = document.getElementById('tableSelect').value;
    const selectedTable = document.getElementById(`table_${selectedValue}`);
    if (selectedTable) {
        selectedTable.classList.remove('hidden');
    }

    if (selectedValue === 'status_alunos') {
        fetchStudentOverallStatusFromBackend();
    } else if (selectedValue === 'login_alunos') {
        fetchLoginAlunosFromBackend();
    }
};

window.addRecord = function() {
    const selectedTable = document.getElementById('tableSelect').value;
    if (selectedTable === 'info_alunos') {
        document.getElementById('addAlunoModal').classList.remove('hidden');
    } else {
        showMessageModal('Aviso', 'A adição de novos registos só está disponível para a tabela "Informações dos Alunos".', 'warning');
    }
};

window.triggerSearch = function() {
    const searchTerm = document.getElementById('searchInput').value;
    window.fetchAlunosFromBackend(1, searchTerm);
}

window.fetchStudentOverallStatusFromBackend = async function() {
    const tbody = document.querySelector('#table_status_alunos tbody');
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">A carregar dados...</td></tr>`;

    try {
        const response = await fetch('http://127.0.0.1:5000/status_alunos');
        if (!response.ok) throw new Error(`Erro HTTP! Status: ${response.status}`);
        
        const statuses = await response.json();
        
        tbody.innerHTML = ''; // Limpa a mensagem "A carregar"

        if (statuses.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">Nenhum status de aluno encontrado.</td></tr>`;
            return;
        }

        statuses.forEach(status => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${status.student_name || ''}</td>
                <td>${status.faltas !== null ? status.faltas : ''}</td>
                <td>${status.situacao || ''}</td>
                <td>-</td> 
                <td>-</td>
            `;
            tbody.appendChild(row);
        });

    } catch (error) {
        console.error('Erro ao buscar status dos alunos:', error);
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: red;">Erro ao carregar dados.</td></tr>`;
    }
};

window.fetchLoginAlunosFromBackend = async function() {
    const tbody = document.querySelector('#table_login_alunos tbody');
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">A carregar dados...</td></tr>`;

    try {
        const response = await fetch('http://127.0.0.1:5000/users');
        if (!response.ok) throw new Error(`Erro HTTP! Status: ${response.status}`);
        
        const users = await response.json();
        
        const studentUsers = users.filter(user => user.role === 'student');

        tbody.innerHTML = '';

        if (studentUsers.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">Nenhum utilizador de aluno encontrado.</td></tr>`;
            return;
        }

        studentUsers.forEach(user => {
            const row = document.createElement('tr');
            const lastLogin = user.last_login ? new Date(user.last_login).toLocaleString('pt-BR') : 'Nunca';
            
            row.innerHTML = `
                <td>${user.username || ''}</td>
                <td>${user.full_name || ''}</td>
                <td>${lastLogin}</td>
                <td>${user.total_logins !== null ? user.total_logins : '0'}</td>
                <td>${user.online_status || 'Offline'}</td>
            `;
            tbody.appendChild(row);
        });

    } catch (error) {
        console.error('Erro ao buscar utilizadores de login:', error);
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: red;">Erro ao carregar dados.</td></tr>`;
    }
};

window.closeAddAlunoModal = () => {
    const modal = document.getElementById('addAlunoModal');
    if (modal) modal.classList.add('hidden');
};

window.closeEditAlunoModal = () => {
    const modal = document.getElementById('editAlunoModal');
    if (modal) modal.classList.add('hidden');
};