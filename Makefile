# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Makefile                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: jdreissi <jdreissi@student.42.fr>          +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2026/07/23 14:42:36 by jdreissi          #+#    #+#              #
#    Updated: 2026/07/25 15:53:40 by jdreissi         ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

NAME = fly_in

CC = Python3

SRCS_DIR = srcs

SRCS = $(SRCS_DIR)/main.py \
	   $(SRCS_DIR)/structure.py \


all: $(NAME)

$(NAME):
	$(CC) $(SRCS)

clean:

fclean: clean

re: fclean all
