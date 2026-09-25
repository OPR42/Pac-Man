# Banner
BANNERSTAMP	= .banner_shown

# Program names
DISP_NAME	= Pac-Man
NAME		= pac-man
FOLDER		= pacman
CONFIG		= data/config.json
HIGHSCORES	= data/hall_of_fame.json
LOG_FOLDER	= data/logs

# Lint targets
FLAKE8_TGT	= ${FOLDER}/ ${NAME}.py
MYPY_TGT	= ${FOLDER}/ ${NAME}.py

#Colors
LIGHT_GRAY		= \033[2m
ORANGE			= \033[1;33m
BLACK			= \033[1;30m
DARK_GRAY		= \033[1;90m
RED				= \033[1;31m
BRIGHT_RED		= \033[1;91m
GREEN			= \033[1;32m
BRIGHT_GREEN	= \033[1;92m
YELLOW			= \033[1;93m
BLUE			= \033[1;34m
BRIGHT_BLUE		= \033[1;94m
MAGENTA			= \033[1;35m
BRIGHT_PURPLE	= \033[1;95m
CYAN			= \033[1;96m
CYAN_ITALIC 	= \033[0;3;96m
WHITE			= \033[1;97m
BROWN			= \33[1;38;2;160;120;80m
BLUE42			= \33[1;38;2;16;32;96m
WHITE_ON_BLUE42	= \33[0;97m\33[0;48;2;16;32;96m
LIGHT_YELLOW 	= \33[1;38;2;223;195;55m\33[48;2;0;0;0m
RESET			= \033[0m

#Format
BOLD		= \033[1m
ITALIC		= \033[3m
UNDERLINE	= \033[4m
CROSS		= \033[9m
FLASH		= \033[5m
NEGATIVE	= \033[7m

# Rules
${BANNERSTAMP}:
				@clear
				@echo "${BOLD}"
				@echo "${BROWN} ╔════════════════════════════════════════════════════════════════════════════════════════════╗"
				@echo "${BROWN} ║${BLUE42}  ◢◤ ◤█             ${BRIGHT_PURPLE}     ▁▁▁▁         ${CYAN_ITALIC}Who ya gonna${RESET}${BRIGHT_PURPLE}   ▁▁  ▁▁▁                        ${BLUE42} █◥ ◥◣  ${BROWN}║"
				@echo "${BROWN} ║${BLUE42} ◢◤  ◢◤             ${BRIGHT_PURPLE}    ╱ ▁▁ ╲▁▁▁▁▁▁▁▁▁▁▁   ${CYAN_ITALIC}call?${RESET}${BRIGHT_PURPLE}   ╱  │╱  ╱▁▁▁▁▁▁▁▁▁               ${BLUE42} ◥◣  ◥◣ ${BROWN}║"
				@echo "${BROWN} ║${BLUE42} ███ █◢             ${BRIGHT_PURPLE}   ╱ ╱▁╱ ╱ ▁▁  ╱ ▁▁▁╱ ▁▁▁▁▁▁▁  ╱ ╱│▁╱ ╱ ▁▁  ╱ ▁▁ ╲              ${BLUE42} ◣█ ███ ${BROWN}║"
				@echo "${BROWN} ║${BLUE42}   █                ${BRIGHT_PURPLE}  ╱ ▁▁▁▁╱ ╱▁╱ ╱ ╱▁▁  ╱▁▁▁▁▁▁╱ ╱ ╱  ╱ ╱ ╱▁╱ ╱ ╱ ╱ ╱              ${BLUE42}    █   ${BROWN}║"
				@echo "${BROWN} ║${BLUE42}  2026              ${BRIGHT_PURPLE} ╱▁╱    ╲▁▁▁▁╱╲▁▁▁╱          ╱▁╱  ╱▁╱╲▁▁▁▁╱▁╱ ╱▁╱               ${BLUE42}  2026  ${BROWN}║"
				@echo "${BROWN} ║${BLUE42}                    ${BRIGHT_PURPLE}                      ${CYAN_ITALIC}I ain't afraid of no ghost${RESET}                ${BLUE42}        ${BROWN}║"
				@echo "${BROWN} ║${BLUE42}   OPR              ${BRIGHT_PURPLE}                                                                ${BLUE42}Kletsol ${BROWN}║"
				@echo "${BROWN} ║${BLUE42}       ${BRIGHT_PURPLE}                         ${CYAN}42 ${BROWN}─ ${BRIGHT_PURPLE}orobert ${BROWN}& ${BRIGHT_PURPLE}lbonnet ${BROWN}─ ${CYAN}2026                        ${BLUE42}       ${BROWN}║"
				@echo "${BROWN} ╚════════════════════════════════════════════════════════════════════════════════════════════╝\n${RESET}"

install:		${BANNERSTAMP}
				@echo "             ${MAGENTA}──╼━━══${RESET} 📦 Installing ${MAGENTA}${DISP_NAME}${RESET} project ${YELLOW}dependencies${RESET} with ${BRIGHT_BLUE}uv${RESET} 📦 ${MAGENTA}═══━━╾──${RESET}\n"; \
				out=$$(uv sync --dev 2>&1); \
				status=$$?; \
				if [ $$status -eq 0 ]; then \
					printf "                                  🔧 %-28b  ${GREEN}✅         ${RESET}\n" "Running ${BRIGHT_BLUE}uv sync --dev${RESET}"; \
					printf "\n            ${MAGENTA}──╼━━══${RESET} ✅ ${MAGENTA}${DISP_NAME}${RESET} project ${YELLOW}dependencies${RESET} installation ${GREEN}complete${RESET} ✅ ${MAGENTA}══━━╾──${RESET}\n\n"; \
					echo "To run ${MAGENTA}${DISP_NAME}${RESET}, type:\n"; \
					echo "${YELLOW}⌨  ${WHITE_ON_BLUE42} make run_uv ${RESET}${YELLOW}↩${RESET}\n"; \
					echo "${ITALIC}OR${RESET}\n"; \
					echo "${YELLOW}⌨  ${WHITE_ON_BLUE42} source .venv/bin/activate ${RESET}${YELLOW}↩${RESET}"; \
					echo "${YELLOW}⌨  ${WHITE_ON_BLUE42} make run ${RESET}${YELLOW}↩${RESET}\n"; \
					echo "${ITALIC}OR${RESET}\n"; \
					echo "${YELLOW}⌨  ${WHITE_ON_BLUE42} source .venv/bin/activate ${RESET}${YELLOW}↩${RESET}"; \
					echo "${YELLOW}⌨  ${WHITE_ON_BLUE42} python3 ${NAME}.py ${CONFIG} ${RESET}${YELLOW}↩${RESET}\n"; \
				else \
					printf "                                 🔧 %-28b  ${RED}❌         ${RESET}${RESET}\n\n" "Running ${BRIGHT_BLUE}uv sync --dev${RESET}"; \
					printf '%s\n' "$$out"; \
					exit $$status; \
				fi

run:			${BANNERSTAMP}
				@echo "                        ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} project ${CYAN}launched${RESET} 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
				python3 ${NAME}.py ${CONFIG}
		
run_uv:			${BANNERSTAMP}
				@echo "                        ${MAGENTA}──╼━━═══${RESET} 🚀 ${MAGENTA}${DISP_NAME}${RESET} project ${CYAN}launched${RESET} 🚀 ${MAGENTA}═══━━╾──${RESET}\n"; \
				uv run python3 ${NAME}.py ${CONFIG}

debug:			${BANNERSTAMP}
				@echo "                           ${MAGENTA}──╼━━═══${RESET} 🪲 Debugging ${MAGENTA}${DISP_NAME}${RESET} 🪲 ${MAGENTA}════━━╾──${RESET}\n"
				python3 -m pdb ${NAME}.py ${CONFIG}

debug_uv:		${BANNERSTAMP}
				@echo "                           ${MAGENTA}──╼━━═══${RESET} 🪲 Debugging ${MAGENTA}${DISP_NAME}${RESET} 🪲 ${MAGENTA}════━━╾──${RESET}\n"
				uv run python3 -m pdb ${NAME}.py ${CONFIG}

lint:			${BANNERSTAMP}
				@echo "                  ${MAGENTA}──╼━━═══${RESET} 🔎 Checking ${MAGENTA}${DISP_NAME}${RESET} compliance to ${BRIGHT_BLUE}lint${RESET} 🔍 ${MAGENTA}════━━╾──${RESET}"; \
				out=$$(uv run flake8 $(FLAKE8_TGT) 2>&1); \
				status=$$?; \
				if [ $$status -eq 0 ]; then \
					printf "\n                                        $(BRIGHT_BLUE)flake8$(RESET) . . . $(BRIGHT_GREEN)✓$(RESET)\n"; \
				else \
					printf '%s\n' "$$out"; \
					printf "\n                                        $(BRIGHT_BLUE)flake8$(RESET) . . . $(RED)✗$(RESET)\n"; \
				fi; \
				out=$$(uv run mypy $(MYPY_TGT) \
					--warn-return-any \
					--warn-unused-ignores \
					--ignore-missing-imports \
					--disallow-untyped-defs \
					--check-untyped-defs 2>&1); \
				status=$$?; \
				if [ $$status -eq 0 ]; then \
					printf "\n                                        $(BRIGHT_BLUE)mypy$(RESET) . . . . $(BRIGHT_GREEN)✓$(RESET)\n\n"; \
				else \
					printf '%s\n' "$$out"; \
					printf "\n                                        $(BRIGHT_BLUE)mypy$(RESET) . . . . $(RED)✗$(RESET)\n\n"; \
				fi

lint-strict:	${BANNERSTAMP}
				@echo "               ${MAGENTA}──╼━━═══${RESET} 🔎 Checking ${MAGENTA}${DISP_NAME}${RESET} strict compliance to ${BRIGHT_BLUE}lint${RESET} 🔍 ${MAGENTA}═══━━╾──${RESET}"; \
				out=$$(uv run flake8 $(FLAKE8_TGT) 2>&1); \
				status=$$?; \
				if [ $$status -eq 0 ]; then \
					printf "\n                                        $(BRIGHT_BLUE)flake8$(RESET) . . . $(BRIGHT_GREEN)✓$(RESET)\n"; \
				else \
					printf '%s\n' "$$out"; \
					printf "\n                                        $(BRIGHT_BLUE)flake8$(RESET) . . . $(RED)✗$(RESET)\n"; \
				fi; \
				out=$$(uv run mypy $(MYPY_TGT) --strict 2>&1); \
				status=$$?; \
				if [ $$status -eq 0 ]; then \
					printf "\n                                        $(BRIGHT_BLUE)mypy$(RESET) . . . . $(BRIGHT_GREEN)✓$(RESET)\n\n"; \
				else \
					printf '%s\n' "$$out"; \
					printf "\n                                        $(BRIGHT_BLUE)mypy$(RESET) . . . . $(RED)✗$(RESET)\n\n"; \
				fi

clean: 			${BANNERSTAMP}
				@echo "                     ${MAGENTA}──╼━━═══${RESET} 🧹 ${YELLOW}Cleaning${RESET} Python cache folders 🧹 ${MAGENTA}═══━━╾──${RESET}"; \
				cache_count=$$(find . \
					-path "./.venv" -prune -o \
					\( -name "__pycache__" -o -name ".mypy_cache" -o -name ".pytest_cache" \) \
					-print | wc -l); \
				pyc_count=$$(find . \
					-path "./.venv" -prune -o \
					-name "*.pyc" \
					-print | wc -l); \
				find . \
					-path "./.venv" -prune -o \
					\( -name "__pycache__" -o -name ".mypy_cache" -o -name ".pytest_cache" \) \
					-exec rm -rf {} +; \
				find . \
					-path "./.venv" -prune -o \
					-name "*.pyc" \
					-exec rm -f {} +; \
				count=$$((cache_count + pyc_count)); \
				printf "\n                     ${MAGENTA}──╼━━═══${RESET} ${GREEN}Cleanup complete${RESET} — items removed: ${CYAN}%d${RESET} ${MAGENTA}════━━╾──${RESET}\n\n" "$$count"

fclean:			clean
				@echo "                 ${MAGENTA}──╼━━═══${RESET} 💥 ${YELLOW}Removing${RESET} project environment artifacts 💥 ${MAGENTA}═══━━╾──${RESET}"; \
				venv_count=$$(find . -type d -name ".venv" -print | wc -l); \
				banner_count=0; \
				config_count=0; \
				highscores_count=0; \
				if [ -f "${BANNERSTAMP}" ]; then \
					banner_count=1; \
				fi; \
				if [ -f "${CONFIG}" ]; then \
					config_count=1; \
					cp -f "${CONFIG}" "${CONFIG}.bak"; \
				fi; \
				if [ -f "${HIGHSCORES}" ]; then \
					highscores_count=1; \
					cp -f "${HIGHSCORES}" "${HIGHSCORES}.bak"; \
				fi; \
				logs_count=$$(find ${LOG_FOLDER} -maxdepth 1 -type f 2>/dev/null | wc -l); \
				find . -type d -name ".venv" -exec rm -rf {} +; \
				rm -f "${BANNERSTAMP}" "${CONFIG}" "${HIGHSCORES}"; \
				if [ -d "${LOG_FOLDER}" ]; then \
				    rm -f ${LOG_FOLDER}/*; \
				fi; \
				count=$$((venv_count + config_count + highscores_count + banner_count + logs_count)); \
				printf "\n                ${MAGENTA}──╼━━═══${RESET} ✅ ${GREEN}Full cleanup complete${RESET} — items removed: ${CYAN}%d${RESET} ✅ ${MAGENTA}═══━━╾──${RESET}\n\n" "$$count"

recall:			${BANNERSTAMP}
				@echo "                  ${MAGENTA}──╼━━═══${RESET} ♻️  ${YELLOW}Recalling${RESET} saved configuration files ♻️  ${MAGENTA}══━━╾──${RESET}"; \
				count=0; \
				if [ -f "${CONFIG}.bak" ]; then \
					mv -f "${CONFIG}.bak" "${CONFIG}"; \
					count=$$((count + 1)); \
				fi; \
				if [ -f "${HIGHSCORES}.bak" ]; then \
					mv -f "${HIGHSCORES}.bak" "${HIGHSCORES}"; \
					count=$$((count + 1)); \
				fi; \
				printf "\n                    ${MAGENTA}──╼━━═══${RESET} ${GREEN}Recall complete${RESET} — items restored: ${CYAN}%d${RESET} ${MAGENTA}════━━╾──${RESET}\n\n" "$$count"

re:				fclean install

keytest:		
				uv run python3 ${FOLDER}/base/utils.py

list_pr_calls:	${BANNERSTAMP}
				@echo "                  ${MAGENTA}──╼━━═══${RESET} 📁  Listing ${MAGENTA}${DISP_NAME}${RESET}'s calls to ${YELLOW}Raylib${RESET} 📁  ${MAGENTA}════━━╾──${RESET}"; \
				grep -rhoE 'pr\.[A-Za-z_][A-Za-z0-9_]*' pacman --include='*.py' | sort | uniq -c | sort -nr

show_pr_calls:	${BANNERSTAMP}
				@echo "                  ${MAGENTA}──╼━━═══${RESET} 📂  Showing ${MAGENTA}${DISP_NAME}${RESET}'s calls to ${YELLOW}Raylib${RESET} 📂  ${MAGENTA}════━━╾──${RESET}"; \
				grep -rnE 'pr\.[A-Za-z_][A-Za-z0-9_]*' pacman --include='*.py'

inventory:		${BANNERSTAMP}
				@echo "                ${MAGENTA}──╼━━═══${RESET} 🗂️  Showing ${MAGENTA}${DISP_NAME}${RESET} project's ${YELLOW}inventory${RESET} 🗂️  ${MAGENTA}═══━━╾──${RESET}"; \
				uv run python tools/inventory.py

.PHONY: install run run_uv debug debug_uv clean fclean recall re lint lint-strict keytest list_pr_calls show_pr_calls show_tree
