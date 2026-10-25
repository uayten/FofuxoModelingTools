**Português** · [English](README.md) (em desenvolvimento)

# Fofuxo Modeling Tools

Add-on para o Blender com ferramentas que agilizam a modelagem e a exportação:

- um checkbox **Angle** dentro do modificador Mirror, que faz ele espelhar num
  plano inclinado a 45°, e não só nos planos X/Y/Z a 90° um do outro;
- o modificador **Merge Collection**, que junta todos os objetos de uma
  collection numa malha só, pronta para exportar;
- o modificador **Spherical Bend**, que curva uma malha plana numa abóbada,
  com pilares e decoração opcionais;
- o modificador **Arabesque**, que transforma um esqueleto de arestas em
  caules de arabesco em relevo.

- [Instalação](#instalação)
- [Uso](#uso)
- [Licença](#licença)

## Instalação

Requer Blender 4.2 ou mais novo.

1. Baixe o `.zip` da página de [Releases](https://github.com/uayten/FofuxoModelingTools/releases).
2. No Blender, arraste o `.zip` para dentro da janela, ou vá em
   *Edit > Preferences > Get Extensions*, abra o menu ⌄ no canto superior
   direito e escolha *Install from Disk*.

Para gerar o `.zip` a partir do código:

```bash
blender --command extension build --source-dir fofuxo_modeling_tools
```

## Uso

O checkbox **Angle** fica no fim do painel do modificador Mirror. Ao marcar,
ele cria um empty oculto, filho do objeto, e o põe como *Mirror Object*: é esse
empty que define o plano do espelho. A rotação dele aparece dentro do
subpainel e pode ser mudada para outro ângulo. Desmarcar apaga o empty.

Os modificadores novos ficam no submenu *Add Modifier > Fofuxo*.

O **Merge Collection** é um modificador Geometry Nodes: escolha a collection no
painel e a malha do objeto passa a conter cópias de todos os objetos dela
(inclusive sub-collections, curvas e textos), já com os modificadores e
materiais deles. A collection entra como está em volta da origem do mundo,
sem rotação, e acompanha o objeto: mover ou girar o suporte move a malha
juntada. Para exportar, use uma malha vazia como suporte e esconda ou exclua a
collection de origem.

- O suporte precisa ser um objeto mesh: empties não aceitam modificadores.
- O suporte não pode estar dentro da collection que ele junta. Isso cria um
  ciclo de dependência e o resultado fica vazio.

O **Spherical Bend** também é Geometry Nodes. O **Dome Height** muda só a
altura da parte curva, como um scale Z nela: 1 deixa a abóbada redonda, abaixo
de 1 achata o topo. O topo fica onde está e a parte reta acompanha o fim do
arco; com *Use Floor* ligado, ela continua indo até o piso.

O **Arabesque** lê só as arestas da malha: desenhe o esqueleto com vértices e
arestas num plano XY do objeto. Cada vértice do esqueleto vira um anel de uma
malha low-poly em relevo, só de quads e aberta (sem tampas nem face de trás).
*Direction* escolhe o lado do plano de onde o relevo sai; *Crest* fecha as
laterais (1 forma uma crista; acima de 1, uma crista mais alta). Largura e
espessura são em unidades do mundo, mesmo com o objeto escalado.

Os inputs *Main Stem* e *Width Group* leem vertex groups: no modificador,
clique no ícone de atributo ao lado do input e escreva o nome do grupo.

- *Main Stem*: os vértices do caule principal. As arestas entre eles formam uma
  faixa contínua, que atravessa as junções sem cortes; as outras arestas viram
  galhos, soldados ao anel do caule no vértice de onde saem. Sem grupo, a malha
  é cortada em cada junção.
- *Width Group*: pesos de 0 a 1. Peso 0 usa *Width*, peso 1 usa *Group Width*
  e os valores intermediários misturam os dois.

As arestas vivas ao longo dos galhos, como a crista, recebem crease. Para
arredondar, ponha um Subdivision Surface depois do modificador. O painel
*Width Variation*, desligado por padrão, afina o caule até as pontas soltas.

Os modificadores Geometry Nodes ficam salvos no `.blend`, então quem abre
o arquivo sem o add-on vê o mesmo resultado.

## Licença

[GPL-3.0-or-later](LICENSE), a mesma licença do Blender.
