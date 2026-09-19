# 🌸 ACCELA - Custom Theme & Aesthetic Music Player

<div align="center">

![ACCELA Banner](theme/app_files/res/logo/accela.png)

**Gerenciador e downloader de jogos estilizado, inspirado em Serial Experiments Lain com tema visual customizado, Music Player embutido e mascote dançante Yume Nikki.**

[![Linux](https://img.shields.io/badge/Platform-Linux-blue?logo=linux)](https://github.com/gabesvr/accela-custom-theme)
[![Python](https://img.shields.io/badge/Python-3.13%2B-yellow?logo=python)](https://python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green?logo=qt)](https://riverbankcomputing.com)

</div>

---

## 🌟 Créditos e Agradecimentos

Este projeto é uma versão customizada construída sobre o trabalho incrível da comunidade:

- **[CiscoSweater (ciskao)](https://github.com/ciscosweater)**: Criador do instalador **[enter-the-wired](https://github.com/ciscosweater/enter-the-wired)** e empacotamento para Linux. Todos os créditos pela engenhosidade dos scripts de instalação e correção de dependências.
- **Tachibana Labs / Morrenus**: Desenvolvedores do cliente **ACCELA** original inspirado em *Serial Experiments Lain*.
- **gabesvr**: Criação e integração do **Aesthetic Music Player**, mascote pixel art Yume Nikki, suporte ao CAVA audio visualizer, nova paleta de cores e temas Sonic/Lain.

---

## ✨ Recursos do Tema Customizado

- 🎵 **Aesthetic Music Player Integrado**: Player de música sem bordas integrado diretamente no rodapé da janela principal.
- 💃 **Mascote Dançante Yume Nikki**: Pixel art animado sincronizado com o status de reprodução das faixas.
- 📊 **Espectro de Áudio CAVA**: Visualizador de frequências em tempo real estilo terminal.
- 🎧 **Playlist Embutida**: Músicas incluídas prontas para tocar (`Snow Strippers`, `WOKAWONA`, etc.) em `~/.local/share/ACCELA/music/`.
- 🖼️ **GIFs Colorizados Dinâmicos**: Animações temáticas de Lain e temas retrô que reagem às cores da interface.
- 🎮 **Atalho e Terminal**: Inicialização tanto pelo menu de aplicativos (`.desktop`) quanto pelo terminal com o comando `accela`.

---

## 🚀 Instalação Rápida (1 Comando)

Abra o terminal e execute:

```bash
curl -fsSL https://raw.githubusercontent.com/gabesvr/accela-custom-theme/main/install.sh | bash
```

> O script detecta automaticamente a sua distribuição Linux (CachyOS/Arch, Debian/Ubuntu, Fedora, OpenSUSE, Void), instala as dependências necessárias, prepara o ACCELA, aplica o tema customizado e configura os atalhos.

---

## 🔑 Configuração Inicial: Chave de API Morrenus

Para pesquisar e baixar jogos pelo botão de busca da interface, configure sua chave de API:

1. Acesse **[hubcapmanifest.com](https://hubcapmanifest.com/)** e faça login com seu Discord.
2. Vá para a página de chaves: **[hubcapmanifest.com/api-keys/user](https://hubcapmanifest.com/api-keys/user)**.
3. Crie uma nova chave de API (*New API Key*).
4. Abra o **ACCELA**, clique no ícone de **Engrenagem (Configurações)** ⚙️.
5. Acesse a aba **Integrações (Integrations)**.
6. Cole a sua chave no campo **Morrenus API Key** e clique em **OK**.

---

## 📖 Como Usar

### 1. Buscando e Baixando
- Clique no ícone de **Lupa** 🔍.
- Digite o nome do jogo desejado e pressione Enter.
- Dê um duplo clique no resultado para iniciar o download.

### 2. Arrastar e Soltar (Sem API Key)
- Se você tiver o arquivo `.zip` de manifesto de um jogo, basta arrastá-lo diretamente para dentro da janela do ACCELA.

### 3. Personalizando Músicas e Cores
- **Adicionar suas músicas**: Basta colar arquivos `.mp3` na pasta `~/.local/share/ACCELA/music/`.
- **Cores & Visual**: No menu de Configurações ⚙️ → aba **Visual**, você pode alterar as cores de destaque e de fundo para combinar com seu rice.

---

## 🛠️ Para quem já tem o ACCELA instalado

Se você já tem o ACCELA instalado e quer apenas aplicar o tema e o player:

```bash
git clone https://github.com/gabesvr/accela-custom-theme.git
cd accela-custom-theme
./apply-theme.sh
```

---

## 📜 Licença e Isenção de Responsabilidade

Este projeto é disponibilizado para fins educacionais e de customização de interface de usuário. Todo o conteúdo multimídia pertence aos seus respectivos detentores de direitos.
Créditos integrais aos criadores originais citados na seção de créditos.
