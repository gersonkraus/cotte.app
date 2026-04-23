const axios = require('axios');

async function criarAgendamentoDeTeste(token) {
  try {
    let clienteId;
    const { data: clientes } = await axios.get('http://127.0.0.1:8000/api/v1/clientes', {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (clientes.length === 0) {
      const { data: novoCliente } = await axios.post('http://127.0.0.1:8000/api/v1/clientes', 
        { nome: 'Cliente de Teste para Agendamento' },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      clienteId = novoCliente.id;
    } else {
      clienteId = clientes[0].id;
    }

    const dataAgendamento = new Date();
    dataAgendamento.setDate(dataAgendamento.getDate() + 1);
    dataAgendamento.setHours(10, 0, 0, 0);

    const payload = {
      cliente_id: clienteId,
      data_agendada: dataAgendamento.toISOString(),
      tipo: 'servico'
    };

    await axios.post('http://127.0.0.1:8000/api/v1/agendamentos', payload, {
      headers: { Authorization: `Bearer ${token}` }
    });
    console.log('Agendamento de teste criado ou já existente.');

  } catch (error) {
    if (error.response && error.response.status === 400 && error.response.data.error && error.response.data.error.message.includes('Conflito')) {
      console.log('Agendamento de teste já existe. Continuando...');
    } else {
      console.error('Erro ao criar/verificar agendamento de teste:', error.response ? JSON.stringify(error.response.data, null, 2) : error.message);
      process.exit(1);
    }
  }
}

async function criarUsuarioDeTeste() {
  try {
    const payload = {
      nome: 'Teste Playwright',
      email: 'teste@playwright.com',
      senha: 'senha123',
      empresa_nome: 'Empresa Playwright'
    };
    const response = await axios.post('http://127.0.0.1:8000/api/v1/auth/registrar', payload);
    console.log('Usuário de teste criado com sucesso:', response.data);
    
    // Logar para obter o token e criar o agendamento
    const { data: loginData } = await axios.post('http://127.0.0.1:8000/api/v1/auth/login', { email: 'teste@playwright.com', senha: 'senha123' });
    await criarAgendamentoDeTeste(loginData.access_token);

  } catch (error) {
    if (error.response && error.response.status === 400) {
      console.log('Usuário de teste já existe. Continuando...');
      // Logar para obter o token e criar o agendamento
      const { data: loginData } = await axios.post('http://127.0.0.1:8000/api/v1/auth/login', { email: 'teste@playwright.com', senha: 'senha123' });
      await criarAgendamentoDeTeste(loginData.access_token);
    } else {
      console.error('Erro ao criar usuário de teste:', error.response ? JSON.stringify(error.response.data, null, 2) : error.message);
      process.exit(1);
    }
  }
}

criarUsuarioDeTeste();