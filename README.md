# USOLINUX

Gerenciador de jogos para Linux baseado no [ACCELA](https://portal3d.github.io/accela-dist-archive/guide.html), com instalação em um comando, SLSsteam configurado automaticamente, tema dreamy Y2K e music player integrado.

<div align="center">

![USOLINUX](assets/screenshot.png)

</div>

## O que o instalador faz

Um único comando deixa tudo pronto:

1. Instala as dependências do sistema e o ACCELA base (scripts do [enter-the-wired](https://github.com/ciscosweater/enter-the-wired)).
2. Baixa a versão mais recente do [SLSsteam](https://github.com/AceSLS/SLSsteam), instala e ativa `PlayNotOwnedGames` e `API` no `~/.config/SLSsteam/config.yaml`, para os jogos aparecerem e abrirem pela Steam.
3. Aplica o tema USOLINUX, o music player e as músicas, e instala o `cava` (visualizador).
4. Configura a janela flutuante no Hyprland, o atalho no menu de aplicativos e o comando `usolinux` no terminal.

Funciona em Arch/CachyOS, Debian/Ubuntu, Fedora, openSUSE e Void.

## Tutorial

### 1. Instalar

Com a Steam instalada, rode no terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/gabesvr/accela-easy-install/main/install.sh | bash
```

O script pede a sua senha (`sudo`) para instalar pacotes. No final aparece **USOLINUX INSTALADO COM SUCESSO**.

### 2. Reiniciar a Steam

Feche a Steam por completo e abra de novo, para ela carregar o SLSsteam.

### 3. Abrir o USOLINUX

- Pelo menu de aplicativos: **USOLINUX**
- Ou pelo terminal: `usolinux`

### 4. Configurar a chave da API (para buscar jogos)

1. Entre com o Discord em [hubcapmanifest.com](https://hubcapmanifest.com/).
2. Pegue sua chave em [hubcapmanifest.com/api-keys/user](https://hubcapmanifest.com/api-keys/user).
3. No USOLINUX, clique na engrenagem → **Integrations**.
4. Cole a chave em **Hubcap API Key** e clique em **OK**.

### 5. Baixar um jogo

- **Pela busca:** clique na lupa, pesquise o jogo e escolha o que baixar.
- **Por arquivo:** arraste um `.zip` de manifest para a janela. Não precisa de chave.

Durante o download aparece a animação com a dançarina de Yume Nikki e a barra de progresso. Quando terminar, reinicie a Steam: o jogo aparece na biblioteca pronto para jogar.

### 6. Biblioteca

O ícone de livro mostra os jogos instalados, o tamanho de cada um e se há atualização.

## Tema

- Gradientes pastel, cards arredondados e botões em pílula na janela principal e em todos os diálogos.
- As cores vêm da cor de destaque e da cor de fundo escolhidas em **Configurações → Style**: mude as duas e o app inteiro acompanha.
- Fontes Nunito (texto) e Silkscreen (títulos pixel), incluídas no tema (SIL Open Font License).
- Music player flutuante com visualizador CAVA em tempo real e mascote de Yume Nikki (clique nele para trocar a dança).

## Músicas

Coloque arquivos `.mp3`, `.flac`, `.ogg`, `.wav` ou `.m4a` em `~/.local/share/ACCELA/music/` ou `~/Music/ACCELA/`. O player toca todos em sequência.

## Já tem o ACCELA instalado?

Aplique só o tema:

```bash
git clone https://github.com/gabesvr/accela-easy-install.git
cd accela-easy-install
./apply-theme.sh
```

Rodar o `install.sh` ou o `apply-theme.sh` de novo atualiza o tema e mantém as suas configurações. As cores do tema só são impostas na primeira vez.

## Problemas comuns

- **O jogo não aparece na Steam:** reinicie a Steam por completo e confira se `~/.config/SLSsteam/config.yaml` tem `PlayNotOwnedGames: yes`.
- **O visualizador do player fica vazio:** instale o `cava` pelo gerenciador de pacotes da sua distro.
- **Nenhuma música toca:** confira se há arquivos de áudio em `~/.local/share/ACCELA/music/`.

## Desenvolvimento

`./dev-sync.sh --run` copia o código de `theme/app_files` para a instalação local e abre o app, sem mexer na configuração.

## Créditos

- Tachibana Labs / Morrenus: ACCELA original.
- [CiscoSweater (ciskao)](https://github.com/ciscosweater): [enter-the-wired](https://github.com/ciscosweater/enter-the-wired), instalador e empacotamento para Linux.
- [AceSLS](https://github.com/AceSLS/SLSsteam): SLSsteam.
- gabesvr: USOLINUX, tema, music player e instalador automático.
