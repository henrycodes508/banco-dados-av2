"""
gui.py - Interface Gráfica do Processador de Consultas SQL

Construída com Tkinter (nativo do Python, sem dependências externas).

Layout:
  +-----------------------------------------------------------+
  |  PROCESSADOR DE CONSULTAS SQL                             |
  +-----------------------------------------------------------+
  |  [ Campo de entrada SQL (Text multilinha) ]               |
  |  [ Botão: Processar Consulta ]  [ Botão: Limpar ]        |
  +-----------------------------------------------------------+
  |  Abas:                                                    |
  |  [ Álgebra Relacional | Otimização | Grafo | Plano Exec ] |
  |                                                           |
  |  Conteúdo da aba selecionada                              |
  +-----------------------------------------------------------+
  |  Barra de status (erros / mensagens)                      |
  +-----------------------------------------------------------+
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font as tkfont

from schema import SCHEMA
from sql_parser import SQLParser, ParsedQuery
from relational_algebra import RelationalAlgebraConverter
from optimizer import QueryOptimizer
from query_tree import QueryTree, TreeNode, NodeType
from execution_plan import ExecutionPlanGenerator


# Tema escuro
BG_COLOR = "#0F172A"
INPUT_BG = "#1E1B4B"  # roxo escuro
TEXT_COLOR = "#E5E7EB"
CANVAS_BG = "#020617"


# Cores para os nós da árvore no Canvas
NODE_COLORS = {
    NodeType.TABLE: "#FFFACD",
    NodeType.SELECTION: "#ADD8E6",
    NodeType.PROJECTION: "#90EE90",
    NodeType.JOIN: "#FFA07A",
}

NODE_BORDER_COLORS = {
    NodeType.TABLE: "#DAA520",
    NodeType.SELECTION: "#4682B4",
    NodeType.PROJECTION: "#228B22",
    NodeType.JOIN: "#CD5C5C",
}


class TreeDrawer:
    """
    Desenha a árvore de operadores em um Canvas Tkinter.
    """

    H_SPACING = 200
    V_SPACING = 90
    NODE_PADX = 14
    NODE_PADY = 8
    MARGIN = 60

    def __init__(self, canvas: tk.Canvas, root_node: TreeNode):
        self.canvas = canvas
        self.root = root_node
        self.positions: dict[int, tuple[float, float]] = {}
        self._leaf_counter = 0

    def draw(self):
        self.canvas.delete("all")
        self.positions = {}
        self._leaf_counter = 0

        if self.root is None:
            return

 # 1) Calcular posições lógicas (grid)
        self._calculate_layout(self.root, depth=0)

# 2) Converter para coordenadas de pixel
        pixel_positions = {}
        for nid, (gx, gy) in self.positions.items():
            px = gx * self.H_SPACING + self.MARGIN
            py = gy * self.V_SPACING + self.MARGIN
            pixel_positions[nid] = (px, py)
        self.positions = pixel_positions

 # 3) Desenhar arestas (linhas)
        self._draw_edges(self.root)
    
# 4) Desenhar nós (retângulos com texto)
        self._draw_nodes(self.root)

 # 5) Ajustar scroll region
        all_x = [p[0] for p in self.positions.values()]
        all_y = [p[1] for p in self.positions.values()]
        if all_x and all_y:
            self.canvas.configure(scrollregion=(
                0, 0,
                max(all_x) + self.H_SPACING + self.MARGIN,
                max(all_y) + self.V_SPACING + self.MARGIN,
            ))

    def _calculate_layout(self, node: TreeNode, depth: int):
        if not node.children:
            self.positions[id(node)] = (self._leaf_counter, depth)
            self._leaf_counter += 1
            return

        for child in node.children:
            self._calculate_layout(child, depth + 1)

        children_x = [self.positions[id(c)][0] for c in node.children]
        avg_x = sum(children_x) / len(children_x)
        self.positions[id(node)] = (avg_x, depth)

    def _draw_edges(self, node: TreeNode):
        if id(node) not in self.positions:
            return
        px, py = self.positions[id(node)]

        for child in node.children:
            if id(child) in self.positions:
                cx, cy = self.positions[id(child)]
                self.canvas.create_line(
                    px, py + 20, cx, cy - 20,
                    fill="#9CA3AF", width=2, arrow=tk.LAST,  # MODIFICADO
                )
            self._draw_edges(child)

    def _draw_nodes(self, node: TreeNode):
        """Desenha um nó como retângulo arredondado com texto."""
        if id(node) not in self.positions:
            return
        x, y = self.positions[id(node)]

        label = node.label
        fill_color = NODE_COLORS.get(node.node_type, "#FFFFFF")
        border_color = NODE_BORDER_COLORS.get(node.node_type, "#000000")

        # Calcular tamanho do texto
        text_id = self.canvas.create_text(x, y, text=label, anchor="center",
                                          font=("Consolas", 9))
        bbox = self.canvas.bbox(text_id)
        self.canvas.delete(text_id)

        if bbox:
            tx1, ty1, tx2, ty2 = bbox
            w = (tx2 - tx1) / 2 + self.NODE_PADX
            h = (ty2 - ty1) / 2 + self.NODE_PADY
        else:
            w, h = 60, 18

        # Retângulo arredondado (simulado com oval + retângulo)
        x1, y1 = x - w, y - h
        x2, y2 = x + w, y + h
        r = 8 # raio de arredondamento


        # Desenhar retângulo arredondado usando polígono
        self.canvas.create_polygon(
            x1 + r, y1,  x2 - r, y1,
            x2, y1,  x2, y1 + r,
            x2, y2 - r,  x2, y2,
            x2 - r, y2,  x1 + r, y2,
            x1, y2,  x1, y2 - r,
            x1, y1 + r,  x1, y1,
            fill=fill_color, outline=border_color, width=2, smooth=True,
        )

        # Texto do nó
        self.canvas.create_text(
            x, y, text=label, anchor="center",
            font=("Consolas", 9), fill="#111827",  # MODIFICADO
        )

        # Recursão para filhos
        for child in node.children:
            self._draw_nodes(child)


# ---------------------------------------------------------------------------
# Interface Gráfica Principal
# ---------------------------------------------------------------------------

class ProcessadorConsultasGUI:

    # Consulta de exemplo pré-carregada
    EXEMPLO_SQL = (
        "SELECT cliente.Nome, pedido.idPedido, pedido.DataPedido, pedido.ValorTotalPedido\n"
        "FROM Cliente\n"
        "JOIN Pedido ON cliente.idCliente = pedido.Cliente_idCliente\n"
        "WHERE cliente.TipoCliente_idTipoCliente = 1 AND pedido.ValorTotalPedido = 0"
    )

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Processador de Consultas SQL")
        self.root.geometry("1100x800")
        self.root.minsize(900, 650)

        self.root.configure(bg=BG_COLOR)  # MODIFICADO

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",
                        background="#0F172A")

        style.configure("TNotebook.Tab",
                        background="#1E3A8A",   # azul escuro
                        foreground="white",     # texto branco
                        padding=8)

        style.map("TNotebook.Tab",
                  background=[("selected", "#1E40AF")],  # azul mais claro ao selecionar
                  foreground=[("selected", "white")])
        
        style.configure("Custom.TLabelframe",
                        background="#2E1065")  # roxo escuro

        style.configure("Custom.TLabelframe.Label",
                        background="#2E1065",
                        foreground="white")  # texto branco
        style.configure("Custom.TButton",
                        background="#1E3A8A",   # azul escuro
                        foreground="white",
                        padding=6)

        style.map("Custom.TButton",
                  background=[("active", "#1E40AF")],  # azul mais claro ao passar mouse
                  foreground=[("active", "white")])
        
        style.configure("Custom.TFrame",
                background="#2E1065")  
        
        style.configure("Custom.TLabel",
                background="#2E1065",  # roxo escuro (igual ao resto)
                foreground="white")

        self._create_widgets()

    def _create_widgets(self):

        # ====== Frame Superior: Entrada SQL ======
        input_frame = ttk.LabelFrame(
            self.root,
            text="  Consulta SQL  ",
            padding=10,
            style="Custom.TLabelframe"  # Modificado
        )
        input_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        self.sql_input = scrolledtext.ScrolledText(
            input_frame, height=6, font=("Consolas", 11),
            wrap=tk.WORD,
            bg=INPUT_BG,  # Modificado
            fg=TEXT_COLOR,  # Modificado
            insertbackground="white"  # Modificado
        )
        self.sql_input.pack(fill=tk.X, pady=(0, 8))
        self.sql_input.insert("1.0", self.EXEMPLO_SQL)

        # Frame de botões
        btn_frame = ttk.Frame(input_frame)
        btn_frame.configure(style="Custom.TFrame")
        btn_frame.pack(fill=tk.X)

        self.btn_process = ttk.Button(
            btn_frame, text="  Processar Consulta  ",
            style="Custom.TButton",  
            command=self._on_process,
        )
        self.btn_process.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_clear = ttk.Button(
            btn_frame, text="  Limpar  ",
            style="Custom.TButton",
            command=self._on_clear,
        )
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_example = ttk.Button(
            btn_frame, text="  Exemplo  ",
            style="Custom.TButton",
            command=self._on_example,
        )
        self.btn_example.pack(side=tk.LEFT, padx=(0, 5))

        # Label com tabelas disponíveis
        tables_str = ", ".join(sorted(SCHEMA.keys()))
        ttk.Label(
            btn_frame,
            text=f"Tabelas: {tables_str}",
            font=("Segoe UI", 8),
            style="Custom.TLabel",  # MODIFICADO
        ).pack(side=tk.RIGHT)

        # ====== Frame Inferior: Resultados (Notebook com abas) ======
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Aba 1: Álgebra Relacional
        self.tab_algebra = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_algebra, text="  Álgebra Relacional  ")
        self.txt_algebra = scrolledtext.ScrolledText(
            self.tab_algebra, font=("Consolas", 11),
            state=tk.DISABLED,
            bg=CANVAS_BG,  # MODIFICADO
            fg="white"  # MODIFICADO
        )
        self.txt_algebra.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Aba 2: Otimização
        self.tab_optim = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_optim, text="  Otimização  ")
        self.txt_optim = scrolledtext.ScrolledText(
            self.tab_optim, font=("Consolas", 11),
            state=tk.DISABLED,
            bg=CANVAS_BG,
            fg="white"
        )
        self.txt_optim.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)


         # Aba 3: Grafo de Operadores
        self.tab_graph = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_graph, text="  Grafo de Operadores  ")


        # Canvas com scrollbars para o grafo
        graph_container = ttk.Frame(self.tab_graph)
        graph_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(graph_container, bg=CANVAS_BG)  # MODIFICADO
        scrollbar_x = ttk.Scrollbar(graph_container, orient=tk.HORIZONTAL, command=self.canvas.xview)
        scrollbar_y = ttk.Scrollbar(graph_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=scrollbar_x.set, yscrollcommand=scrollbar_y.set)

        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Aba 4: Plano de Execução
        self.tab_plan = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_plan, text="  Plano de Execução  ")
        self.txt_plan = scrolledtext.ScrolledText(
            self.tab_plan, font=("Consolas", 11),
            state=tk.DISABLED,
            bg=CANVAS_BG,
            fg="white"
        )
        self.txt_plan.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)


        # ====== Barra de Status ======
        self.status_var = tk.StringVar(value="Pronto. Digite uma consulta SQL e clique em 'Processar Consulta'.")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor=tk.W,
            padding=(10, 4),
            background=BG_COLOR,  # MODIFICADO
            foreground="white"  # MODIFICADO
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 10))


        # Aba 5: Árvore Texto (representação textual da árvore)
        self.tab_tree_text = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tree_text, text="  Árvore (Texto)  ")
        self.txt_tree = scrolledtext.ScrolledText(
            self.tab_tree_text, font=("Consolas", 11),
            state=tk.DISABLED,
            bg=CANVAS_BG,
            fg="white"
        )
        self.txt_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # -------------------------------------------------------------------
    # Callbacks
    # -------------------------------------------------------------------

    def _on_process(self):
        """
        Callback do botão 'Processar Consulta'.
        Executa o pipeline completo: Parse -> AR -> Otimização -> Grafo -> Plano
        """
        sql = self.sql_input.get("1.0", tk.END).strip()
        if not sql:
            self.status_var.set("Erro: Consulta SQL vazia.")
            return

        try:
            # 1) PARSING E VALIDAÇÃO
            parser = SQLParser()
            parsed = parser.parse(sql)
            self.status_var.set("Consulta parseada e validada com sucesso.")

            # 2) CONVERSÃO PARA ÁLGEBRA RELACIONAL
            converter = RelationalAlgebraConverter(parsed)
            algebra_expr = converter.convert()
            self._display_algebra(algebra_expr, parsed)

            # 3) OTIMIZAÇÃO
            optimizer = QueryOptimizer(parsed)
            steps = optimizer.optimize()
            self._display_optimization(algebra_expr, steps)

            # 4) CONSTRUÇÃO DA ÁRVORE
            tree = QueryTree(parsed, optimizer)
            root_node = tree.build()
            self._display_tree(tree, root_node)

            # 5) PLANO DE EXECUÇÃO
            planner = ExecutionPlanGenerator(tree)
            plan_steps = planner.generate()
            plan_text = planner.format_plan()
            self._display_plan(plan_text)

            self.status_var.set("Processamento concluído com sucesso.")
            self.notebook.select(0)  # Ir para primeira aba

        except ValueError as e:
            self.status_var.set("Erro de validação (veja detalhes abaixo).")
            self._clear_results()
            self._set_text(self.txt_algebra, f"ERRO DE VALIDAÇÃO:\n\n{str(e)}")
            messagebox.showerror("Erro de Validação", str(e))

        except Exception as e:
            self.status_var.set(f"Erro inesperado: {type(e).__name__}")
            self._clear_results()
            self._set_text(self.txt_algebra, f"ERRO INESPERADO:\n\n{type(e).__name__}: {str(e)}")
            messagebox.showerror("Erro", f"{type(e).__name__}: {str(e)}")

    def _on_clear(self):
        """Limpa a entrada e os resultados."""
        self.sql_input.delete("1.0", tk.END)
        self._clear_results()
        self.status_var.set("Pronto.")

    def _on_example(self):
        """Carrega a consulta de exemplo."""
        self.sql_input.delete("1.0", tk.END)
        self.sql_input.insert("1.0", self.EXEMPLO_SQL)
        self.status_var.set("Exemplo carregado. Clique em 'Processar Consulta'.")

    # -------------------------------------------------------------------
    # Exibição de resultados
    # -------------------------------------------------------------------

    def _display_algebra(self, expression: str, parsed: ParsedQuery):
        """Exibe a álgebra relacional na aba correspondente."""
        text = []
        text.append("=" * 60)
        text.append("  CONVERSÃO SQL  →  ÁLGEBRA RELACIONAL")
        text.append("=" * 60)
        text.append("")
        text.append("SQL Original:")
        text.append(f"  {parsed.original_sql}")
        text.append("")
        text.append("─" * 60)
        text.append("")
        text.append("Álgebra Relacional (conversão direta):")
        text.append("")
        text.append(f"  {expression}")
        text.append("")
        text.append("─" * 60)
        text.append("")
        text.append("Detalhes do parsing:")
        text.append(f"  Tabelas envolvidas: {', '.join(parsed.all_tables_original.values())}")
        text.append(f"  Número de JOINs:    {len(parsed.joins)}")
        text.append(f"  Condições WHERE:    {len(parsed.where_conditions)}")
        text.append(f"  Colunas SELECT:     {len(parsed.select_columns)}")

        self._set_text(self.txt_algebra, "\n".join(text))

    def _display_optimization(self, original_expr: str, steps: list):
        """Exibe os passos de otimização na aba correspondente."""
        text = []
        text.append("=" * 60)
        text.append("  OTIMIZAÇÃO DA CONSULTA")
        text.append("=" * 60)
        text.append("")
        text.append("Expressão original (antes da otimização):")
        text.append(f"  {original_expr}")
        text.append("")

        for i, step in enumerate(steps, 1):
            text.append("─" * 60)
            text.append("")
            text.append(f"PASSO {i} — {step.name}")
            text.append("")
            text.append(f"  {step.description}")
            text.append("")
            text.append("  Resultado:")
            text.append(f"  {step.expression}")
            text.append("")

        text.append("─" * 60)

        self._set_text(self.txt_optim, "\n".join(text))

    def _display_tree(self, tree: QueryTree, root_node: TreeNode):
        """Exibe o grafo de operadores (Canvas visual + texto)."""
        # Desenhar no Canvas
        drawer = TreeDrawer(self.canvas, root_node)
        drawer.draw()

        # Exibir representação textual na aba de texto
        tree_text = []
        tree_text.append("=" * 60)
        tree_text.append("  ÁRVORE DE OPERADORES (GRAFO OTIMIZADO)")
        tree_text.append("=" * 60)
        tree_text.append("")
        tree_text.append("Legenda:")
        tree_text.append("  Tabela    → Nó folha (tabela base)")
        tree_text.append("  σ (sigma) → Seleção (filtro de tuplas)")
        tree_text.append("  π (pi)    → Projeção (filtro de colunas)")
        tree_text.append("  ⋈ (join)  → Junção")
        tree_text.append("")
        tree_text.append("Árvore:")
        tree_text.append("")
        tree_text.append(tree.to_text())
        tree_text.append("")

        self._set_text(self.txt_tree, "\n".join(tree_text))

    def _display_plan(self, plan_text: str):
        """Exibe o plano de execução na aba correspondente."""
        self._set_text(self.txt_plan, plan_text)

    # -------------------------------------------------------------------
    # Utilitários
    # -------------------------------------------------------------------

    def _set_text(self, widget: scrolledtext.ScrolledText, text: str):
        """Define o texto de um widget ScrolledText (que está desabilitado)."""
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state=tk.DISABLED)

    def _clear_results(self):
        """Limpa todas as abas de resultado."""
        for widget in (self.txt_algebra, self.txt_optim, self.txt_plan, self.txt_tree):
            self._set_text(widget, "")
        self.canvas.delete("all")

    def run(self):
        """Inicia o loop principal da interface gráfica."""
        self.root.mainloop()
