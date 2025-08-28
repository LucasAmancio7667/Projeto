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

window.fetchAlunosFromBackend = async function() {
    try {
        const response = await fetch('http://127.0.0.1:5000/alunos');
        if (!response.ok) throw new Error(`Erro HTTP! Status: ${response.status}`);
        let alunos = await response.json();
        alunos.sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR', { sensitivity: 'base' }));
        displayAlunosInInfoTable(alunos);
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

window.fetchStudentOverallStatusFromBackend = async function() { /* ...código completo... */ };
function displayStudentOverallStatusTable(statuses) { /* ...código completo... */ };
window.fetchLoginAlunosFromBackend = async function() { /* ...código completo... */ };
function displayLoginAlunosTable(users) { /* ...código completo... */ };
window.fetchAtividadesAlunosFromBackend = async function() { /* ...código completo... */ };
function displayAtividadesAlunosTable(atividades) { /* ...código completo... */ };
function validateAlunoForm(alunoData, isEdit = false) { /* ...código completo... */ };

// *** FUNÇÃO CORRIGIDA ***
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
            // *** AQUI ESTÁ A CORREÇÃO ***
            // Força a atualização da tabela de alunos imediatamente.
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
                await window.fetchAlunosFromBackend(); // Atualiza a tabela após excluir
            } else {
                showMessageModal('Erro', 'Erro ao excluir aluno: ' + (data.message || 'Erro desconhecido.'), 'error');
            }
        } catch (error) {
            showMessageModal('Erro de Conexão', 'Não foi possível conectar ao servidor para excluir o aluno.', 'error');
        }
    });
};

window.editAluno = async function(alunoId) { /* ...código completo... */ };
async function sendEditedAlunoToBackend(alunoId, alunoData) { /* ...código completo... */ };
window.changeTable = function() { /* ...código completo... */ };
window.searchTable = function() { /* ...código completo... */ };
window.addRecord = function() { /* ...código completo... */ };
window.editRecord = function() { /* ...código completo... */ };
window.closeAddAlunoModal = () => { /* ...código completo... */ };
window.closeEditAlunoModal = () => { /* ...código completo... */ };

// Cole as definições completas das funções que estão resumidas para garantir que nada falte
// ... (código completo das funções de fetch, display, validate, etc., como na resposta anterior)
window.fetchStudentOverallStatusFromBackend = async function() {
    try {
        const response = await fetch('http://127.0.0.1:5000/status_alunos');
        if (!response.ok) throw new Error(`Erro HTTP! Status: ${response.status}`);
        let statuses = await response.json();
        statuses.sort((a, b) => a.student_name.localeCompare(b.student_name, 'pt-BR', { sensitivity: 'base' }));
        displayStudentOverallStatusTable(statuses);
    } catch (error) { console.error('Erro ao buscar status:', error); }
};
function displayStudentOverallStatusTable(statuses) {
    const tbody = document.querySelector('#table_status_alunos tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (statuses.length === 0) { tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">Nenhum status encontrado.</td></tr>`; return; }
    statuses.forEach(status => {
        const row = document.createElement('tr');
        row.innerHTML = `<td>${status.student_name || ''}</td><td>${status.faltas || 0}</td><td>${status.situacao || ''}</td><td>-</td><td>-</td>`;
        tbody.appendChild(row);
    });
};
window.fetchLoginAlunosFromBackend = async function() {
    try {
        const response = await fetch('http://127.0.0.1:5000/users');
        if (!response.ok) throw new Error(`Erro HTTP! Status: ${response.status}`);
        let users = await response.json();
        users.sort((a, b) => (a.full_name || '').localeCompare((b.full_name || ''), 'pt-BR', { sensitivity: 'base' }));
        displayLoginAlunosTable(users);
    } catch (error) { console.error('Erro ao buscar usuários:', error); }
};
function displayLoginAlunosTable(users) {
    const tbody = document.querySelector('#table_login_alunos tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (users.length === 0) { tbody.innerHTML = `<tr><td colspan="5" style="text-align: center;">Nenhum usuário encontrado.</td></tr>`; return; }
    users.forEach(user => {
        const lastLogin = user.last_login ? new Date(user.last_login).toLocaleString('pt-BR') : 'Nunca';
        const row = document.createElement('tr');
        row.innerHTML = `<td>${user.username || ''}</td><td>${user.full_name || ''}</td><td>${lastLogin}</td><td>${user.total_logins !== null ? user.total_logins : ''}</td><td>${user.online_status || ''}</td>`;
        tbody.appendChild(row);
    });
};
window.fetchAtividadesAlunosFromBackend = async function() {
  try {
      const response = await fetch('http://127.0.0.1:5000/atividades_alunos');
      if (!response.ok) throw new Error(`Erro HTTP! Status: ${response.status}`);
      let atividades = await response.json();
      atividades.sort((a, b) => (a.student_name || '').localeCompare((b.student_name || ''), 'pt-BR', { sensitivity: 'base' }));
      displayAtividadesAlunosTable(atividades);
  } catch (error) { console.error('Erro ao buscar atividades:', error); }
};
function displayAtividadesAlunosTable(atividades) {
    const tbody = document.querySelector('#table_atividades_alunos tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (atividades.length === 0) { tbody.innerHTML = `<tr><td colspan="12" style="text-align: center;">Nenhuma atividade encontrada.</td></tr>`; return; }
    atividades.forEach(atividade => {
        const row = document.createElement('tr');
        let aulasHtml = '';
        for (let i = 1; i <= 10; i++) { aulasHtml += `<td>${atividade[`aula_${i}`] || 'Pendente'}</td>`; }
        row.innerHTML = `<td>${atividade.student_name || ''}</td>${aulasHtml}<td>${atividade.total_enviadas !== null ? atividade.total_enviadas : ''}</td><td></td>`;
        tbody.appendChild(row);
    });
};
function validateAlunoForm(alunoData, isEdit = false) {
  if (!alunoData.turma) { showMessageModal('Campo Obrigatório', 'O campo "Turma" é obrigatório.', 'warning'); return false; }
  if (!alunoData.nome) { showMessageModal('Campo Obrigatório', 'O campo "Nome" é obrigatório.', 'warning'); return false; }
  if (!alunoData.cpf) { showMessageModal('Campo Obrigatório', 'O campo "CPF" é obrigatório.', 'warning'); return false; }
  if (!alunoData.responsavel) { showMessageModal('Campo Obrigatório', 'O campo "Responsável" é obrigatório.', 'warning'); return false; }
  if (!alunoData.escolaridade) { showMessageModal('Campo Obrigatório', 'O campo "Escolaridade" é obrigatório.', 'warning'); return false; }
  if (!alunoData.escola) { showMessageModal('Campo Obrigatório', 'O campo "Escola" é obrigatório.', 'warning'); return false; }
  if (!isEdit && !alunoData.data_nascimento) { showMessageModal('Campo Obrigatório', 'O campo "Data de Nascimento" é obrigatório.', 'warning'); return false; }
  if (alunoData.nome.length > 70) { showMessageModal('Campo Inválido', 'O campo "Nome" deve ter no máximo 70 caracteres.', 'warning'); return false; }
  if (/[0-9!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]+/.test(alunoData.nome)) { showMessageModal('Campo Inválido', 'O campo "Nome" não deve conter números ou símbolos.', 'warning'); return false; }
  if (alunoData.email && alunoData.email.length > 50) { showMessageModal('Campo Inválido', 'O campo "Email" deve ter no máximo 50 caracteres.', 'warning'); return false; }
  if (alunoData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(alunoData.email)) { showMessageModal('Campo Inválido', 'O campo "Email" está em um formato inválido.', 'warning'); return false; }
  if (alunoData.telefone && !/^[0-9]{0,11}$/.test(alunoData.telefone)) { showMessageModal('Campo Inválido', 'O campo "Telefone" deve conter apenas números e ter no máximo 11 dígitos.', 'warning'); return false; }
  if (alunoData.rg && !/^[0-9]{7,9}$/.test(alunoData.rg)) { showMessageModal('Campo Inválido', 'O campo "RG" deve conter apenas números e ter entre 7 e 9 dígitos.', 'warning'); return false; }
  if (alunoData.cpf && !/^[0-9]{11}$/.test(alunoData.cpf)) { showMessageModal('Campo Inválido', 'O campo "CPF" deve conter apenas números e ter 11 dígitos.', 'warning'); return false; }
  if (alunoData.endereco && alunoData.endereco.length > 100) { showMessageModal('Campo Inválido', 'O campo "Endereço" deve ter no máximo 100 caracteres.', 'warning'); return false; }
  if (alunoData.responsavel.length > 70) { showMessageModal('Campo Inválido', 'O campo "Responsável" deve ter no máximo 70 caracteres.', 'warning'); return false; }
  if (/[0-9!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]+/.test(alunoData.responsavel)) { showMessageModal('Campo Inválido', 'O campo "Responsável" não deve conter números ou símbolos.', 'warning'); return false; }
  return true;
};
window.editAluno = async function(alunoId) {
    try {
        const response = await fetch(`http://127.0.0.1:5000/alunos/${alunoId}`);
        if (!response.ok) throw new Error(`Erro HTTP! Status: ${response.status}`);
        const aluno = await response.json();
        if (aluno) {
            document.getElementById('editAlunoId').value = aluno.id;
            document.getElementById('editTurma').value = aluno.turma || '';
            document.getElementById('editNome').value = aluno.nome || '';
            document.getElementById('editEmail').value = aluno.email || '';
            document.getElementById('editTelefone').value = aluno.telefone || '';
            document.getElementById('editDataNascimento').value = aluno.data_nascimento || '';
            document.getElementById('editRg').value = aluno.rg || '';
            document.getElementById('editCpf').value = aluno.cpf || '';
            document.getElementById('editEndereco').value = aluno.endereco || '';
            document.getElementById('editEscolaridade').value = aluno.escolaridade || '';
            document.getElementById('editEscola').value = aluno.escola || '';
            document.getElementById('editResponsavel').value = aluno.responsavel || '';
            document.getElementById('editAlunoModal').classList.remove('hidden');
        } else { showMessageModal('Erro', 'Aluno não encontrado para edição.', 'error'); }
    } catch (error) { showMessageModal('Erro', 'Não foi possível carregar os dados do aluno para edição.', 'error'); }
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
            await window.fetchAlunosFromBackend();
        } else { showMessageModal('Erro', 'Erro ao atualizar aluno: ' + (data.message || 'Erro desconhecido.'), 'error'); }
    } catch (error) { showMessageModal('Erro de Conexão', 'Não foi possível conectar ao servidor para atualizar o aluno.', 'error'); }
}
window.changeTable = function() {
    const selectedTable = document.getElementById('tableSelect').value;
    document.querySelectorAll('.database-table-container').forEach(table => table.classList.add('hidden'));
    document.getElementById(`table_${selectedTable}`).classList.remove('hidden');
    if (selectedTable === 'info_alunos') window.fetchAlunosFromBackend();
    else if (selectedTable === 'status_alunos') window.fetchStudentOverallStatusFromBackend();
    else if (selectedTable === 'login_alunos') window.fetchLoginAlunosFromBackend();
    else if (selectedTable === 'atividades_alunos') window.fetchAtividadesAlunosFromBackend();
};
window.searchTable = function() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const activeTable = document.querySelector('.database-table-container:not(.hidden)');
    if (activeTable) {
        activeTable.querySelectorAll('tbody tr').forEach(row => {
            row.style.display = row.textContent.toLowerCase().includes(searchTerm) ? '' : 'none';
        });
    }
};
window.addRecord = function() {
    const selectedTable = document.getElementById('tableSelect').value;
    if (selectedTable === 'info_alunos') {
        document.getElementById('addAlunoModal').classList.remove('hidden');
    } else { showMessageModal('Aviso', `Funcionalidade indisponível para a tabela: ${selectedTable}`, 'warning'); }
};
window.editRecord = function() {
    const selectedTable = document.getElementById('tableSelect').value;
    if (selectedTable === 'info_alunos') {
        showMessageModal('Instrução', 'Clique no ícone "✏️" ao lado de cada aluno para editar.', 'info');
    } else { showMessageModal('Aviso', `Funcionalidade indisponível para a tabela: ${selectedTable}`, 'warning'); }
};
window.closeAddAlunoModal = () => {
    document.getElementById('addAlunoModal').classList.add('hidden');
    document.getElementById('addAlunoForm').reset();
};
window.closeEditAlunoModal = () => {
    document.getElementById('editAlunoModal').classList.add('hidden');
    document.getElementById('editAlunoForm').reset();
};