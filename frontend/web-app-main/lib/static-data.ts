import { Trail } from "./types"

export const staticTrails: Trail[] = [
  {
    id: "trail-1",
    topic: "Transformer Architecture",
    createdAt: "2024-12-01",
    nodes: [
      {
        id: "n1",
        paper: {
          id: "p1",
          title: "Attention Is All You Need",
          authors: ["Vaswani, A.", "Shazeer, N.", "Parmar, N.", "Uszkoreit, J."],
          year: 2017,
          abstract:
            "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
          url: "https://arxiv.org/abs/1706.03762",
          isRead: true,
        },
        dependencies: [],
      },
      {
        id: "n2",
        paper: {
          id: "p2",
          title: "BERT: Pre-training of Deep Bidirectional Transformers",
          authors: ["Devlin, J.", "Chang, M.", "Lee, K.", "Toutanova, K."],
          year: 2018,
          abstract:
            "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.",
          url: "https://arxiv.org/abs/1810.04805",
          isRead: true,
        },
        dependencies: ["n1"],
      },
      {
        id: "n3",
        paper: {
          id: "p3",
          title: "GPT-2: Language Models are Unsupervised Multitask Learners",
          authors: ["Radford, A.", "Wu, J.", "Child, R.", "Luan, D."],
          year: 2019,
          abstract:
            "Natural language processing tasks, such as question answering, machine translation, reading comprehension, and summarization, are typically approached with supervised learning on taskspecific datasets. We demonstrate that language models begin to learn these tasks without any explicit supervision when trained on a new dataset of millions of web pages called WebText.",
          url: "https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf",
          isRead: false,
        },
        dependencies: ["n1"],
      },
      {
        id: "n4",
        paper: {
          id: "p4",
          title: "RoBERTa: A Robustly Optimized BERT Pretraining Approach",
          authors: ["Liu, Y.", "Ott, M.", "Goyal, N.", "Du, J."],
          year: 2019,
          abstract:
            "Language model pretraining has led to significant performance gains but careful comparison between different approaches is challenging. Training is computationally expensive, often done on private datasets of different sizes, and, as we will show, hyperparameter choices have significant impact on the final results. We present a replication study of BERT pretraining that carefully measures the impact of many key hyperparameters and training data size.",
          url: "https://arxiv.org/abs/1907.11692",
          isRead: false,
        },
        dependencies: ["n2"],
      },
      {
        id: "n5",
        paper: {
          id: "p5",
          title: "GPT-3: Language Models are Few-Shot Learners",
          authors: ["Brown, T.", "Mann, B.", "Ryder, N.", "Subbiah, M."],
          year: 2020,
          abstract:
            "Recent work has demonstrated substantial gains on many NLP tasks and benchmarks by pre-training on a large corpus of text followed by fine-tuning on a specific task. While typically task-agnostic in architecture, this method still requires task-specific fine-tuning datasets of thousands or tens of thousands of examples. By contrast, humans can generally perform a new language task from only a few examples or from simple instructions.",
          url: "https://arxiv.org/abs/2005.14165",
          isRead: false,
        },
        dependencies: ["n3"],
      },
      {
        id: "n6",
        paper: {
          id: "p6",
          title: "Vision Transformer (ViT): An Image is Worth 16x16 Words",
          authors: ["Dosovitskiy, A.", "Beyer, L.", "Kolesnikov, A."],
          year: 2020,
          abstract:
            "While the Transformer architecture has become the de-facto standard for natural language processing tasks, its applications to computer vision remain limited. In vision, attention is either applied in conjunction with convolutional networks, or used to replace certain components of convolutional networks while keeping their overall structure in place. We show that this reliance on CNNs is not necessary and a pure transformer applied directly to sequences of image patches can perform very well on image classification tasks.",
          url: "https://arxiv.org/abs/2010.11929",
          isRead: false,
        },
        dependencies: ["n2", "n5"],
      },
    ],
  },
  {
    id: "trail-2",
    topic: "Reinforcement Learning",
    createdAt: "2024-11-15",
    nodes: [
      {
        id: "rl1",
        paper: {
          id: "rl-p1",
          title: "Playing Atari with Deep Reinforcement Learning",
          authors: ["Mnih, V.", "Kavukcuoglu, K.", "Silver, D."],
          year: 2013,
          abstract:
            "We present the first deep learning model to successfully learn control policies directly from high-dimensional sensory input using reinforcement learning. The model is a convolutional neural network, trained with a variant of Q-learning, whose input is raw pixels and whose output is a value function estimating future rewards.",
          url: "https://arxiv.org/abs/1312.5602",
          isRead: true,
        },
        dependencies: [],
      },
      {
        id: "rl2",
        paper: {
          id: "rl-p2",
          title: "Human-level Control through Deep Reinforcement Learning",
          authors: ["Mnih, V.", "Kavukcuoglu, K.", "Silver, D.", "Rusu, A."],
          year: 2015,
          abstract:
            "The theory of reinforcement learning provides a normative account, deeply rooted in psychological and neuroscientific perspectives on animal behaviour, of how agents may optimize their control of an environment. To use reinforcement learning successfully in situations approaching real-world complexity, however, agents are confronted with a difficult task: they must derive efficient representations of the environment from high-dimensional sensory inputs, and use these to generalize past experience to new situations.",
          url: "https://www.nature.com/articles/nature14236",
          isRead: true,
        },
        dependencies: ["rl1"],
      },
      {
        id: "rl3",
        paper: {
          id: "rl-p3",
          title: "Proximal Policy Optimization Algorithms",
          authors: ["Schulman, J.", "Wolski, F.", "Dhariwal, P."],
          year: 2017,
          abstract:
            "We propose a new family of policy gradient methods for reinforcement learning, which alternate between sampling data through interaction with the environment, and optimizing a surrogate objective function using stochastic gradient ascent. Whereas standard policy gradient methods perform one gradient update per data sample, we propose a novel objective function that enables multiple epochs of minibatch updates.",
          url: "https://arxiv.org/abs/1707.06347",
          isRead: false,
        },
        dependencies: ["rl1"],
      },
      {
        id: "rl4",
        paper: {
          id: "rl-p4",
          title: "Mastering the Game of Go with Deep Neural Networks and Tree Search",
          authors: ["Silver, D.", "Huang, A.", "Maddison, C."],
          year: 2016,
          abstract:
            "The game of Go has long been viewed as the most challenging of classic games for artificial intelligence owing to its enormous search space and the difficulty of evaluating board positions and moves. Here we introduce a new approach to computer Go that uses value networks to evaluate board positions and policy networks to select moves.",
          url: "https://www.nature.com/articles/nature16961",
          isRead: false,
        },
        dependencies: ["rl2", "rl3"],
      },
    ],
  },
  {
    id: "trail-3",
    topic: "Diffusion Models",
    createdAt: "2025-01-05",
    nodes: [
      {
        id: "dm1",
        paper: {
          id: "dm-p1",
          title: "Denoising Diffusion Probabilistic Models",
          authors: ["Ho, J.", "Jain, A.", "Abbeel, P."],
          year: 2020,
          abstract:
            "We present high quality image synthesis results using diffusion probabilistic models, a class of latent variable models inspired by considerations from nonequilibrium thermodynamics. Our best results are obtained by training on a weighted variational bound designed according to a novel connection between diffusion probabilistic models and denoising score matching with Langevin dynamics.",
          url: "https://arxiv.org/abs/2006.11239",
          isRead: false,
        },
        dependencies: [],
      },
      {
        id: "dm2",
        paper: {
          id: "dm-p2",
          title: "High-Resolution Image Synthesis with Latent Diffusion Models",
          authors: ["Rombach, R.", "Blattmann, A.", "Lorenz, D."],
          year: 2022,
          abstract:
            "By decomposing the image formation process into a sequential application of denoising autoencoders, diffusion models (DMs) achieve state-of-the-art synthesis results on image data and beyond. Additionally, their formulation allows for a guiding mechanism to control the image generation process without retraining. However, since these models typically operate directly in pixel space, optimization of powerful DMs often consumes hundreds of GPU days and inference is expensive due to sequential evaluations.",
          url: "https://arxiv.org/abs/2112.10752",
          isRead: false,
        },
        dependencies: ["dm1"],
      },
      {
        id: "dm3",
        paper: {
          id: "dm-p3",
          title: "Classifier-Free Diffusion Guidance",
          authors: ["Ho, J.", "Salimans, T."],
          year: 2022,
          abstract:
            "Classifier guidance is a recently introduced method to trade off mode coverage and sample fidelity in conditional diffusion models post training, in the same spirit as low temperature sampling or truncation in other types of generative models. Classifier guidance combines the score estimate of a diffusion model with the gradient of an image classifier and thereby requires training an image classifier separate from the diffusion model.",
          url: "https://arxiv.org/abs/2207.12598",
          isRead: false,
        },
        dependencies: ["dm1"],
      },
    ],
  },
]
