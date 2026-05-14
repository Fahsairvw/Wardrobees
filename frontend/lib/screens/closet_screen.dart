import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/wardrobe.dart';
import '../models/cloth_item.dart';
import 'clothing_item.dart';

class ClosetScreen extends StatefulWidget {
  const ClosetScreen({super.key});

  @override
  State<ClosetScreen> createState() => _ClosetScreenState();
}

class _ClosetScreenState extends State<ClosetScreen> {
  int _selectedIndex = 1; // Closet is at index 1 in navigation
  late Future<Wardrobe> _wardrobeFuture;
  final int _userId = 1; // TODO: Get from user session/auth
  
  // Define the 3 main groups in order with their category mappings
  final Map<String, List<String>> _groupMapping = {
    'Tops': ['short sleeve top', 'long sleeve top', 'short sleeve outwear', 'long sleeve outwear', 'vest', 'sling'],
    'Bottoms': ['shorts', 'trousers', 'skirt'],
    'Dresses': ['short sleeve dress', 'long sleeve dress', 'vest dress', 'sling dress'],
  };

  @override
  void initState() {
    super.initState();
    _wardrobeFuture = ApiService.getWardrobe(_userId);
  }

  void _onNavTap(int index) {
    if (index == _selectedIndex) return;
    
    setState(() {
      _selectedIndex = index;
    });
    
    // Navigate to different screens based on index
    switch (index) {
      case 0:
        Navigator.of(context).pushReplacementNamed('/home');
        break;
      case 1:
        // Already on closet
        break;
      case 2:
        // TODO: Add detect screen route
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Detect feature coming soon')),
        );
        break;
      case 3:
        // TODO: Add search screen route
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Search feature coming soon')),
        );
        break;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFFFDF7),
      appBar: AppBar(
        backgroundColor: const Color(0xFFFFFDF7),
        elevation: 0,
        title: const Text(
          'Closet',
          style: TextStyle(
            color: Colors.black,
            fontSize: 32,
            fontFamily: 'Inter',
            fontWeight: FontWeight.w700,
          ),
        ),
        centerTitle: false,
      ),
      body: FutureBuilder<Wardrobe>(
        future: _wardrobeFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error_outline, size: 48, color: Colors.red),
                  const SizedBox(height: 16),
                  Text('Error: ${snapshot.error}'),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () {
                      setState(() {
                        _wardrobeFuture = ApiService.getWardrobe(_userId);
                      });
                    },
                    child: const Text('Retry'),
                  ),
                ],
              ),
            );
          }

          if (!snapshot.hasData) {
            return const Center(child: Text('No wardrobe data'));
          }

          final wardrobe = snapshot.data!;

          if (wardrobe.grouped.isEmpty) {
            return const Center(child: Text('Your closet is empty'));
          }

          // Re-group categories by group name
          final groupedByGroup = <String, List<ClothItem>>{};
          _groupMapping.forEach((groupName, categories) {
            final items = <ClothItem>[];
            for (var category in categories) {
              if (wardrobe.grouped.containsKey(category)) {
                items.addAll(wardrobe.grouped[category]!);
              }
            }
            if (items.isNotEmpty) {
              groupedByGroup[groupName] = items;
            }
          });

          if (groupedByGroup.isEmpty) {
            return const Center(child: Text('Your closet is empty - no matching categories'));
          }

          return SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (var entry in groupedByGroup.entries)
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildCategorySection(entry.key, entry.value),
                        const SizedBox(height: 24),
                      ],
                    ),
                ],
              ),
            ),
          );
        },
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: _onNavTap,
        backgroundColor: const Color(0xFFFFFDF7),
        selectedItemColor: Colors.teal,
        unselectedItemColor: Colors.grey,
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.home),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.checkroom),
            label: 'Closet',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.photo_camera),
            label: 'Detect',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.search),
            label: 'Search',
          ),
        ],
      ),
    );
  }

  Widget _buildCategorySection(String categoryName, List<ClothItem> items) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          categoryName.replaceFirst(categoryName[0], categoryName[0].toUpperCase()),
          style: const TextStyle(
            color: Colors.black,
            fontSize: 18,
            fontFamily: 'Inter',
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        Container(
          decoration: ShapeDecoration(
            color: const Color(0xFFFFF0F5),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20),
            ),
          ),
          padding: const EdgeInsets.all(12),
          child: GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 0.75,
            ),
            itemCount: items.length,
            itemBuilder: (context, index) {
              return _buildClothingItem(items[index]);
            },
          ),
        ),
      ],
    );
  }

  Widget _buildClothingItem(ClothItem item) {
    final imageUrl = ApiService.getImageUrl(item.imageUrl);

    return Container(
      decoration: ShapeDecoration(
        image: DecorationImage(
          image: NetworkImage(imageUrl),
          fit: BoxFit.cover,
          onError: (exception, stackTrace) {
          },
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () async {
            final result = await Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => ClothingItemScreen(item: item),
              ),
            );
            // Refresh wardrobe if item was deleted
            if (result == true) {
              setState(() {
                _wardrobeFuture = ApiService.getWardrobe(_userId);
              });
            }
          },
          borderRadius: BorderRadius.circular(16),
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              gradient: LinearGradient(
                begin: Alignment.bottomCenter,
                end: Alignment.topCenter,
                colors: [
                  Colors.black.withOpacity(0.3),
                  Colors.transparent,
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
